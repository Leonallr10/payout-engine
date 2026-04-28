from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from payouts.models import LedgerEntry, Merchant, Payout
from payouts.views import get_merchant_balance


@skipUnlessDBFeature("has_select_for_update")
class PayoutConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.merchant = Merchant.objects.create(
            name="Concurrent Merchant",
            email="concurrent@example.com",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=10000,
            entry_type=LedgerEntry.EntryType.CREDIT,
            reference="initial-credit",
        )
        self.url = "/api/v1/payouts"

    def _submit_payout(self, key_suffix: str):
        close_old_connections()
        client = APIClient()
        response = client.post(
            self.url,
            {
                "merchant_id": self.merchant.id,
                "amount_paise": 6000,
                "bank_account_id": f"bank_acc_{key_suffix}",
                "idempotency_key": f"concurrency-key-{key_suffix}",
            },
            format="json",
        )
        close_old_connections()
        return response.status_code, response.json()

    @patch("payouts.views.process_payout.delay")
    def test_two_simultaneous_sixty_rupee_requests_on_hundred_rupee_balance(
        self, mock_delay
    ):
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(self._submit_payout, "a"),
                executor.submit(self._submit_payout, "b"),
            ]
            results = [future.result() for future in futures]

        status_codes = sorted(status_code for status_code, _payload in results)

        self.assertEqual(status_codes, [400, 201])
        self.assertEqual(Payout.objects.count(), 1)
        self.assertEqual(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                entry_type=LedgerEntry.EntryType.DEBIT,
            ).count(),
            1,
        )
        self.assertEqual(get_merchant_balance(self.merchant), 4000)
        mock_delay.assert_called_once()
