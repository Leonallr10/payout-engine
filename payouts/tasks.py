import random

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Payout
from .state_machine import InvalidPayoutTransition, mark_processing_retry, transition_payout

STUCK_TIMEOUT_SECONDS = 30
MAX_PROCESSING_ATTEMPTS = 3
SUCCESS_RATE = 0.7
FAILURE_RATE = 0.2


def _pick_next_pending_payout() -> Payout | None:
    with transaction.atomic():
        payout = (
            Payout.objects.select_for_update(skip_locked=True)
            .filter(status=Payout.Status.PENDING)
            .order_by("id")
            .first()
        )
        if not payout:
            return None
        return transition_payout(payout.id, Payout.Status.PROCESSING)


def _simulate_outcome() -> str:
    value = random.random()
    if value < SUCCESS_RATE:
        return Payout.Status.COMPLETED
    if value < SUCCESS_RATE + FAILURE_RATE:
        return Payout.Status.FAILED
    return "STUCK"


@shared_task(bind=True, max_retries=0)
def process_payout(self, payout_id: int | None = None) -> dict:
    try:
        if payout_id is None:
            payout = _pick_next_pending_payout()
            if payout is None:
                return {"status": "noop", "detail": "No pending payouts available."}
        else:
            payout = Payout.objects.get(pk=payout_id)
            if payout.status == Payout.Status.PENDING:
                payout = transition_payout(payout.id, Payout.Status.PROCESSING)
            elif payout.status in {Payout.Status.COMPLETED, Payout.Status.FAILED}:
                return {"status": "noop", "payout_id": payout.id, "detail": "Terminal payout."}

        outcome = _simulate_outcome()
        if outcome == Payout.Status.COMPLETED:
            payout = transition_payout(payout.id, Payout.Status.COMPLETED)
        elif outcome == Payout.Status.FAILED:
            payout = transition_payout(payout.id, Payout.Status.FAILED)
        else:
            check_stuck_payout.apply_async(
                args=[payout.id],
                countdown=STUCK_TIMEOUT_SECONDS,
            )
            payout.refresh_from_db(fields=["status", "attempts", "processing_started_at"])

        return {
            "payout_id": payout.id,
            "status": payout.status if outcome == "STUCK" else outcome,
            "attempts": payout.attempts,
        }
    except (Payout.DoesNotExist, InvalidPayoutTransition) as exc:
        return {"status": "error", "detail": str(exc)}


@shared_task(bind=True, max_retries=0)
def check_stuck_payout(self, payout_id: int) -> dict:
    try:
        payout = Payout.objects.get(pk=payout_id)
    except Payout.DoesNotExist as exc:
        return {"status": "error", "detail": str(exc)}

    if payout.status != Payout.Status.PROCESSING:
        return {"status": "noop", "payout_id": payout_id, "detail": "Payout no longer processing."}

    if not payout.processing_started_at:
        return {"status": "noop", "payout_id": payout_id, "detail": "Missing processing timestamp."}

    age_seconds = (timezone.now() - payout.processing_started_at).total_seconds()
    if age_seconds <= STUCK_TIMEOUT_SECONDS:
        return {"status": "noop", "payout_id": payout_id, "detail": "Payout not stuck yet."}

    if payout.attempts >= MAX_PROCESSING_ATTEMPTS:
        payout = transition_payout(payout.id, Payout.Status.FAILED)
        return {"payout_id": payout.id, "status": payout.status, "attempts": payout.attempts}

    payout = mark_processing_retry(payout.id)
    retry_delay = STUCK_TIMEOUT_SECONDS * (2 ** max(payout.attempts - 2, 0))
    process_payout.apply_async(args=[payout.id], countdown=retry_delay)

    return {
        "payout_id": payout.id,
        "status": payout.status,
        "attempts": payout.attempts,
        "retry_in_seconds": retry_delay,
    }
