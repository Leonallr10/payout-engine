from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from payouts.models import LedgerEntry, Merchant, Payout
from payouts.state_machine import transition_payout
from payouts.tasks import check_stuck_payout, process_payout


class PayoutTaskTests(TestCase):
    def setUp(self) -> None:
        self.merchant = Merchant.objects.create(
            name="Task Merchant",
            email="task@example.com",
        )
        self.payout = Payout.objects.create(
            merchant=self.merchant,
            amount_paise=4000,
            status=Payout.Status.PENDING,
            bank_account_id="bank_acc_task",
            idempotency_key="task-key",
            attempts=0,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=4000,
            entry_type=LedgerEntry.EntryType.DEBIT,
            reference=f"payout:{self.payout.id}",
        )

    @patch("payouts.tasks.random.random", return_value=0.3)
    def test_process_payout_marks_completed_on_success(self, _mock_random):
        result = process_payout.run(self.payout.id)

        self.payout.refresh_from_db()
        self.assertEqual(result["status"], Payout.Status.COMPLETED)
        self.assertEqual(self.payout.status, Payout.Status.COMPLETED)
        self.assertEqual(self.payout.attempts, 1)

    @patch("payouts.tasks.random.random", return_value=0.8)
    def test_process_payout_marks_failed_and_refunds_on_failure(self, _mock_random):
        result = process_payout.run(self.payout.id)

        self.payout.refresh_from_db()
        self.assertEqual(result["status"], Payout.Status.FAILED)
        self.assertEqual(self.payout.status, Payout.Status.FAILED)
        self.assertEqual(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                entry_type=LedgerEntry.EntryType.CREDIT,
                reference=f"payout_refund:{self.payout.id}",
            ).count(),
            1,
        )

    @patch("payouts.tasks.check_stuck_payout.apply_async")
    @patch("payouts.tasks.random.random", return_value=0.95)
    def test_process_payout_schedules_stuck_check(self, _mock_random, mock_apply_async):
        result = process_payout.run(self.payout.id)

        self.payout.refresh_from_db()
        self.assertEqual(result["status"], Payout.Status.PROCESSING)
        self.assertEqual(self.payout.status, Payout.Status.PROCESSING)
        mock_apply_async.assert_called_once_with(
            args=[self.payout.id],
            countdown=30,
        )

    @patch("payouts.tasks.process_payout.apply_async")
    def test_check_stuck_payout_retries_with_exponential_backoff(self, mock_apply_async):
        transition_payout(self.payout.id, Payout.Status.PROCESSING)
        self.payout.refresh_from_db()
        self.payout.processing_started_at = timezone.now() - timedelta(seconds=31)
        self.payout.save(update_fields=["processing_started_at"])

        result = check_stuck_payout.run(self.payout.id)

        self.payout.refresh_from_db()
        self.assertEqual(result["status"], Payout.Status.PROCESSING)
        self.assertEqual(self.payout.status, Payout.Status.PROCESSING)
        self.assertEqual(self.payout.attempts, 2)
        mock_apply_async.assert_called_once_with(args=[self.payout.id], countdown=30)

    def test_check_stuck_payout_fails_after_max_attempts(self):
        self.payout.status = Payout.Status.PROCESSING
        self.payout.attempts = 3
        self.payout.processing_started_at = timezone.now() - timedelta(seconds=31)
        self.payout.save(update_fields=["status", "attempts", "processing_started_at"])

        result = check_stuck_payout.run(self.payout.id)

        self.payout.refresh_from_db()
        self.assertEqual(result["status"], Payout.Status.FAILED)
        self.assertEqual(self.payout.status, Payout.Status.FAILED)
        self.assertEqual(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                entry_type=LedgerEntry.EntryType.CREDIT,
                reference=f"payout_refund:{self.payout.id}",
            ).count(),
            1,
        )
