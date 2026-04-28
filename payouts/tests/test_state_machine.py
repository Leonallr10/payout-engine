from django.test import TestCase

from payouts.models import LedgerEntry, Merchant, Payout
from payouts.state_machine import InvalidPayoutTransition, transition_payout


class PayoutStateMachineTests(TestCase):
    def setUp(self) -> None:
        self.merchant = Merchant.objects.create(
            name="State Machine Merchant",
            email="state-machine@example.com",
        )
        self.payout = Payout.objects.create(
            merchant=self.merchant,
            amount_paise=5000,
            status=Payout.Status.PENDING,
            bank_account_id="bank_acc_state",
            idempotency_key="state-key",
            attempts=0,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=5000,
            entry_type=LedgerEntry.EntryType.DEBIT,
            reference=f"payout:{self.payout.id}",
        )

    def test_pending_to_processing_to_completed_is_allowed(self):
        payout = transition_payout(self.payout.id, Payout.Status.PROCESSING)
        self.assertEqual(payout.status, Payout.Status.PROCESSING)
        self.assertEqual(payout.attempts, 1)

        payout = transition_payout(self.payout.id, Payout.Status.COMPLETED)
        self.assertEqual(payout.status, Payout.Status.COMPLETED)

    def test_processing_to_failed_refunds_funds_once(self):
        transition_payout(self.payout.id, Payout.Status.PROCESSING)
        payout = transition_payout(self.payout.id, Payout.Status.FAILED)

        self.assertEqual(payout.status, Payout.Status.FAILED)
        self.assertEqual(
            LedgerEntry.objects.filter(
                merchant=self.merchant,
                entry_type=LedgerEntry.EntryType.CREDIT,
                reference=f"payout_refund:{self.payout.id}",
            ).count(),
            1,
        )

    def test_illegal_transition_is_blocked(self):
        with self.assertRaises(InvalidPayoutTransition):
            transition_payout(self.payout.id, Payout.Status.COMPLETED)

        transition_payout(self.payout.id, Payout.Status.PROCESSING)
        transition_payout(self.payout.id, Payout.Status.COMPLETED)

        with self.assertRaises(InvalidPayoutTransition):
            transition_payout(self.payout.id, Payout.Status.PENDING)

    def test_failed_payout_cannot_transition_again(self):
        transition_payout(self.payout.id, Payout.Status.PROCESSING)
        transition_payout(self.payout.id, Payout.Status.FAILED)

        with self.assertRaises(InvalidPayoutTransition):
            transition_payout(self.payout.id, Payout.Status.COMPLETED)
