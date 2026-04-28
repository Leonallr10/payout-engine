from rest_framework import serializers

from .models import LedgerEntry, Merchant, Payout


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ["id", "name", "email"]


class BalanceSerializer(serializers.Serializer):
    merchant = MerchantSerializer()
    balance_paise = serializers.IntegerField()


class CreatePayoutSerializer(serializers.Serializer):
    merchant_id = serializers.IntegerField()
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=255)
    idempotency_key = serializers.CharField(max_length=255)


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            "id",
            "merchant",
            "amount_paise",
            "status",
            "bank_account_id",
            "idempotency_key",
            "attempts",
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "merchant",
            "amount_paise",
            "entry_type",
            "reference",
        ]
