from django.core.management.base import BaseCommand
from django.db import transaction

from payouts.models import LedgerEntry, Merchant

SEED_MERCHANTS = [
    {
        "name": "BlueKart",
        "email": "ops@bluekart.example.com",
        "credits": [120000, 85000, 43000],
    },
    {
        "name": "QuickGrocer",
        "email": "finance@quickgrocer.example.com",
        "credits": [150000, 92000, 61000],
    },
    {
        "name": "Playto Pay Demo Store",
        "email": "merchant@playtopay.example.com",
        "credits": [200000, 175000, 98000],
    },
]


class Command(BaseCommand):
    help = "Seed demo merchants and customer payment credits."

    @transaction.atomic
    def handle(self, *args, **options):
        created_merchants = 0
        created_ledger_entries = 0

        for merchant_seed in SEED_MERCHANTS:
            merchant, was_created = Merchant.objects.get_or_create(
                email=merchant_seed["email"],
                defaults={"name": merchant_seed["name"]},
            )

            if not was_created and merchant.name != merchant_seed["name"]:
                merchant.name = merchant_seed["name"]
                merchant.save(update_fields=["name"])

            created_merchants += int(was_created)

            for index, amount in enumerate(merchant_seed["credits"], start=1):
                _, ledger_created = LedgerEntry.objects.get_or_create(
                    merchant=merchant,
                    reference=f"seed_credit:{merchant.email}:{index}",
                    defaults={
                        "amount_paise": amount,
                        "entry_type": LedgerEntry.EntryType.CREDIT,
                    },
                )
                created_ledger_entries += int(ledger_created)

            balance = (
                LedgerEntry.objects.filter(
                    merchant=merchant,
                    entry_type=LedgerEntry.EntryType.CREDIT,
                )
                .values_list("amount_paise", flat=True)
            )
            total_credit = sum(balance)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Merchant {merchant.name} ready with credit balance {total_credit} paise."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_merchants} merchants created, "
                f"{created_ledger_entries} credit ledger entries added."
            )
        )
