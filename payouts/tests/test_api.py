from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from payouts.models import IdempotencyKey, LedgerEntry, Merchant, Payout


class PayoutApiTests(APITestCase):
    def setUp(self) -> None:
        self.merchant = Merchant.objects.create(
            name="Playto Pay Merchant",
            email="merchant@example.com",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=10000,
            entry_type=LedgerEntry.EntryType.CREDIT,
            reference="initial-fund",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=2500,
            entry_type=LedgerEntry.EntryType.DEBIT,
            reference="service-fee",
        )

    def test_get_balance_aggregates_credits_and_debits(self):
        response = self.client.get(
            reverse("merchant-balance", kwargs={"merchant_id": self.merchant.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["balance_paise"], 7500)
        self.assertEqual(response.data["merchant"]["id"], self.merchant.id)

    @patch("payouts.views.process_payout.delay")
    def test_create_payout_rejects_when_balance_is_insufficient(self, mock_delay):
        payload = {
            "merchant_id": self.merchant.id,
            "amount_paise": 9000,
            "bank_account_id": "bank_acc_123",
            "idempotency_key": "idem-insufficient",
        }

        response = self.client.post(reverse("payouts"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payout.objects.count(), 0)
        self.assertEqual(response.data["available_balance_paise"], 7500)
        mock_delay.assert_not_called()

    def test_list_endpoints_return_merchant_filtered_history(self):
        payout = Payout.objects.create(
            merchant=self.merchant,
            amount_paise=1000,
            status=Payout.Status.COMPLETED,
            bank_account_id="bank_acc_999",
            idempotency_key="history-key",
            attempts=1,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=1000,
            entry_type=LedgerEntry.EntryType.DEBIT,
            reference=f"payout:{payout.id}",
        )

        payouts_response = self.client.get(
            reverse("payouts"), {"merchant_id": self.merchant.id}
        )
        ledger_response = self.client.get(
            reverse("ledger"), {"merchant_id": self.merchant.id}
        )

        self.assertEqual(payouts_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ledger_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(payouts_response.data), 1)
        self.assertGreaterEqual(len(ledger_response.data), 3)
        self.assertEqual(
            IdempotencyKey.objects.filter(
                merchant=self.merchant, key="history-key"
            ).count(),
            0,
        )
