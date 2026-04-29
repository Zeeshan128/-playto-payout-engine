from django.core.management.base import BaseCommand
from payouts.models import Merchant, LedgerEntry


class Command(BaseCommand):
    def handle(self, *args, **kwargs):

        m1 = Merchant.objects.filter(name="Zeeshan").first()

        if not m1:
            m1 = Merchant.objects.create(name="Zeeshan")

        LedgerEntry.objects.create(
            merchant=m1,
            type="credit",
            amount_paise=20013
        )

        self.stdout.write("✅ Seed data added")