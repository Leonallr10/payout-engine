from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from payouts.models import IdempotencyKey, LedgerEntry, Merchant, Payout


class PayoutIdempotencyTests(APITestCase):
    def setUp(self) -> None:
        self.merchant = Merchant.objects.create(
            name="Idempotent Merchant",
            email="idempotent@example.com",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=10000,
            entry_type=LedgerEntry.EntryType.CREDIT,
            reference="seed-credit",
        )

    @patch("payouts.views.process_payout.delay")
    def test_same_key_returns_same_response_without_duplicate_payout(self, mock_delay):
        payload = {
            "merchant_id": self.merchant.id,
            "amount_paise": 6000,
            "bank_account_id": "bank_acc_same_key",
            "idempotency_key": "same-key-123",
        }

        with self.captureOnCommitCallbacks(execute=True):
            first_response = self.client.post(reverse("payouts"), payload, format="json")
        second_response = self.client.post(reverse("payouts"), payload, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data, second_response.data)
        self.assertEqual(Payout.objects.count(), 1)
        self.assertEqual(
            IdempotencyKey.objects.filter(
                merchant=self.merchant,
                key=payload["idempotency_key"],
            ).count(),
            1,
        )
        self.assertEqual(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                entry_type=LedgerEntry.EntryType.DEBIT,
                reference=f"payout:{first_response.data['id']}",
            ).count(),
            1,
        )
        mock_delay.assert_called_once()
