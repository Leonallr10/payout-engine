from django.db import models


class Merchant(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "CREDIT", "Credit"
        DEBIT = "DEBIT", "Debit"

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    amount_paise = models.BigIntegerField()
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    reference = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.entry_type} {self.amount_paise} for {self.merchant_id}"


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="payouts",
    )
    amount_paise = models.BigIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    bank_account_id = models.CharField(max_length=255)
    idempotency_key = models.CharField(max_length=255)
    attempts = models.PositiveIntegerField(default=0)
    processing_started_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "idempotency_key"],
                name="unique_payout_idempotency_per_merchant",
            ),
        ]

    def __str__(self) -> str:
        return f"Payout {self.id} ({self.status})"


class IdempotencyKey(models.Model):
    key = models.CharField(max_length=255)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
    )
    response_body = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "key"],
                name="unique_idempotency_key_per_merchant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.key} for {self.merchant_id}"
