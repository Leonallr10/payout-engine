from django.db import transaction
from django.db.models import BigIntegerField, Case, F, Sum, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import IdempotencyKey, LedgerEntry, Merchant, Payout
from .serializers import (
    BalanceSerializer,
    CreatePayoutSerializer,
    LedgerEntrySerializer,
    PayoutSerializer,
)
from .tasks import process_payout


def get_merchant_balance(merchant: Merchant) -> int:
    balance = (
        LedgerEntry.objects.filter(merchant=merchant)
        .aggregate(
            balance=Coalesce(
                Sum(
                    Case(
                        When(
                            entry_type=LedgerEntry.EntryType.CREDIT,
                            then=F("amount_paise"),
                        ),
                        When(
                            entry_type=LedgerEntry.EntryType.DEBIT,
                            then=Value(-1) * F("amount_paise"),
                        ),
                        default=Value(0),
                        output_field=BigIntegerField(),
                    )
                ),
                0,
                output_field=BigIntegerField(),
            )
        )
        .get("balance", 0)
    )
    return int(balance or 0)


class MerchantBalanceView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, merchant_id: int) -> Response:
        merchant = get_object_or_404(Merchant, pk=merchant_id)
        payload = {
            "merchant": merchant,
            "balance_paise": get_merchant_balance(merchant),
        }
        serializer = BalanceSerializer(payload)
        return Response(serializer.data)


class PayoutListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        merchant_id = request.query_params.get("merchant_id")
        payouts = Payout.objects.all().order_by("-id")
        if merchant_id:
            payouts = payouts.filter(merchant_id=merchant_id)

        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)

    def post(self, request) -> Response:
        serializer = CreatePayoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        with transaction.atomic():
            merchant = get_object_or_404(
                Merchant.objects.select_for_update(),
                pk=validated_data["merchant_id"],
            )

            existing_key = IdempotencyKey.objects.select_for_update().filter(
                merchant=merchant,
                key=validated_data["idempotency_key"],
            ).first()

            if existing_key and existing_key.response_body:
                return Response(existing_key.response_body, status=status.HTTP_200_OK)

            balance_paise = get_merchant_balance(merchant)
            amount_paise = validated_data["amount_paise"]

            if balance_paise < amount_paise:
                error_payload = {
                    "detail": "Insufficient balance for payout.",
                    "available_balance_paise": balance_paise,
                }
                if existing_key:
                    existing_key.response_body = error_payload
                    existing_key.save(update_fields=["response_body"])
                else:
                    IdempotencyKey.objects.create(
                        merchant=merchant,
                        key=validated_data["idempotency_key"],
                        response_body=error_payload,
                    )
                return Response(error_payload, status=status.HTTP_400_BAD_REQUEST)

            payout = Payout.objects.create(
                merchant=merchant,
                amount_paise=amount_paise,
                status=Payout.Status.PENDING,
                bank_account_id=validated_data["bank_account_id"],
                idempotency_key=validated_data["idempotency_key"],
                attempts=0,
            )

            LedgerEntry.objects.create(
                merchant=merchant,
                amount_paise=amount_paise,
                entry_type=LedgerEntry.EntryType.DEBIT,
                reference=f"payout:{payout.id}",
            )

            response_payload = PayoutSerializer(payout).data

            if existing_key:
                existing_key.response_body = response_payload
                existing_key.save(update_fields=["response_body"])
            else:
                IdempotencyKey.objects.create(
                    merchant=merchant,
                    key=validated_data["idempotency_key"],
                    response_body=response_payload,
                )

            transaction.on_commit(lambda: process_payout.delay(payout.id))

        return Response(response_payload, status=status.HTTP_201_CREATED)


class LedgerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        merchant_id = request.query_params.get("merchant_id")
        entries = LedgerEntry.objects.all().order_by("-id")
        if merchant_id:
            entries = entries.filter(merchant_id=merchant_id)

        serializer = LedgerEntrySerializer(entries, many=True)
        return Response(serializer.data)
