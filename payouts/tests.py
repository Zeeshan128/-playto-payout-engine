from django.test import TestCase
from threading import Thread
from rest_framework.test import APIClient

from .models import Merchant, LedgerEntry, Payout


class PayoutTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Create merchant
        self.merchant = Merchant.objects.create(name="Test")

        # Add ₹100 (10000 paise)
        LedgerEntry.objects.create(
            merchant=self.merchant,
            type="credit",
            amount_paise=10000
        )

    # 🔥 Concurrency test
    def make_request(self):
        self.client.post(
            f"/api/v1/payouts/{self.merchant.id}/",
            {"amount_paise": 6000},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(id(self))
        )

    def test_concurrent_payouts(self):
        t1 = Thread(target=self.make_request)
        t2 = Thread(target=self.make_request)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        payouts = Payout.objects.all()

        # Only ONE payout should be created
        self.assertEqual(payouts.count(), 1)

    # 🔁 Idempotency test
    def test_idempotency(self):
        key = "same-key"

        res1 = self.client.post(
            f"/api/v1/payouts/{self.merchant.id}/",
            {"amount_paise": 1000},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key
        )

        res2 = self.client.post(
            f"/api/v1/payouts/{self.merchant.id}/",
            {"amount_paise": 1000},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key
        )

        self.assertEqual(res1.data["id"], res2.data["id"])


from django.test import TestCase

# Create your tests here.
