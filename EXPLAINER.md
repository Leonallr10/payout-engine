# Payout Engine Explainer

This document answers five core architecture questions for the Playto Pay payout engine.

## 1. How does the system prevent duplicate payouts?

Duplicate payouts are prevented with an idempotency layer and a database constraint.

- The client sends an `idempotency_key` in `POST /api/v1/payouts`
- The backend locks the merchant row using `SELECT FOR UPDATE`
- Inside the same transaction, it checks `IdempotencyKey`
- If the same key already has a stored response, the API returns that original response instead of creating a new payout
- The `Payout` model also has a unique constraint on `(merchant, idempotency_key)` as a last line of defense

Why this matters:

- client retries do not create duplicate transfers
- transient network errors are safer
- replayed requests become deterministic

## 2. How is double spending prevented when two payout requests arrive together?

Double spending is prevented by transactional locking plus recomputing the balance inside the lock.

Flow:

1. lock the merchant row with `select_for_update()`
2. calculate the latest ledger-derived balance while holding the lock
3. compare the requested payout amount to available balance
4. create the payout and corresponding debit only if enough funds remain

This means two simultaneous `60 INR` payout requests on a `100 INR` balance cannot both succeed. One request wins the lock first, reserves funds, and the second request sees the reduced balance and fails.

## 3. How does payout processing work in the background?

The payout is created synchronously, but actual payout processing happens asynchronously through Celery.

Flow:

1. API creates a `PENDING` payout and a matching `DEBIT` ledger entry
2. after the DB transaction commits, the API enqueues `process_payout`
3. Celery picks the payout and transitions it to `PROCESSING`
4. outcome simulation is:
   - 70% `COMPLETED`
   - 20% `FAILED`
   - 10% `STUCK`
5. stuck payouts are revisited after 30 seconds

This separation keeps the API fast while still modeling real-world async bank processing.

## 4. How does the payout state machine enforce valid lifecycle transitions?

The state machine explicitly limits legal status changes.

Allowed transitions:

- `PENDING -> PROCESSING`
- `PROCESSING -> COMPLETED`
- `PROCESSING -> FAILED`

Blocked examples:

- `COMPLETED -> PENDING`
- `FAILED -> COMPLETED`
- `PENDING -> COMPLETED`

All transitions are executed in atomic transactions. Illegal transitions raise `InvalidPayoutTransition`, which protects the system from accidental or out-of-order status changes.

## 5. What happens when a payout fails or gets stuck?

Failure handling is built into the state machine and Celery retry flow.

### Failure path

When a payout transitions to `FAILED`:

- the transition happens atomically
- a compensating `CREDIT` ledger entry is created
- the refund is keyed by `payout_refund:<payout_id>` so it is only created once

This returns reserved funds back to the merchant balance.

### Stuck path

If a payout stays in `PROCESSING` for more than 30 seconds:

- `check_stuck_payout` treats it as stuck
- the system retries processing with exponential backoff
- the retry counter is capped at 3 attempts
- after max attempts, the payout is marked `FAILED`
- the failure transition triggers the atomic refund

This models a safe operational pattern:

- fast success when possible
- controlled retries for temporary issues
- explicit failure plus refund when the payout cannot be completed

## Summary

The design focuses on correctness first:

- idempotency prevents replay duplication
- row locks prevent overspending under concurrency
- the state machine blocks invalid status changes
- Celery handles async processing and retry behavior
- compensating ledger credits preserve accounting integrity on failure

If your assignment provided a different exact set of five questions, this document can be adjusted quickly, but these are the five most important questions the current implementation answers.
