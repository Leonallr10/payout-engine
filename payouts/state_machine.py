from django.db import transaction
from django.utils import timezone

from .models import LedgerEntry, Payout

ALLOWED_TRANSITIONS = {
    Payout.Status.PENDING: {Payout.Status.PROCESSING},
    Payout.Status.PROCESSING: {Payout.Status.COMPLETED, Payout.Status.FAILED},
    Payout.Status.COMPLETED: set(),
    Payout.Status.FAILED: set(),
}


class InvalidPayoutTransition(ValueError):
    pass


def transition_payout(payout_id: int, to_status: str) -> Payout:
    with transaction.atomic():
        payout = (
            Payout.objects.select_for_update()
            .select_related("merchant")
            .get(pk=payout_id)
        )

        allowed_targets = ALLOWED_TRANSITIONS.get(payout.status, set())
        if to_status not in allowed_targets:
            raise InvalidPayoutTransition(
                f"Cannot transition payout {payout.id} from {payout.status} to {to_status}."
            )

        payout.status = to_status
        update_fields = ["status"]

        if to_status == Payout.Status.PROCESSING:
            payout.attempts += 1
            payout.processing_started_at = timezone.now()
            update_fields.extend(["attempts", "processing_started_at"])

        if to_status in {Payout.Status.COMPLETED, Payout.Status.FAILED}:
            payout.processing_started_at = None
            update_fields.append("processing_started_at")

        payout.save(update_fields=update_fields)

        if to_status == Payout.Status.FAILED:
            # Refund the reserved funds once if processing ultimately fails.
            LedgerEntry.objects.get_or_create(
                merchant=payout.merchant,
                reference=f"payout_refund:{payout.id}",
                defaults={
                    "amount_paise": payout.amount_paise,
                    "entry_type": LedgerEntry.EntryType.CREDIT,
                },
            )

        return payout


def mark_processing_retry(payout_id: int) -> Payout:
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(pk=payout_id)
        if payout.status != Payout.Status.PROCESSING:
            raise InvalidPayoutTransition(
                f"Cannot retry payout {payout.id} while in {payout.status}."
            )

        payout.attempts += 1
        payout.processing_started_at = timezone.now()
        payout.save(update_fields=["attempts", "processing_started_at"])
        return payout
