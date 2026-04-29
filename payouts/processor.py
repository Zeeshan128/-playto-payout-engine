import random
import time
from django.db import transaction
from django.utils import timezone

from .models import Payout, LedgerEntry


# ✅ State machine rules
ALLOWED_TRANSITIONS = {
    "pending": ["processing"],
    "processing": ["completed", "failed"],
}


def can_transition(old, new):
    return new in ALLOWED_TRANSITIONS.get(old, [])


def retry_payout(payout_id):
    # 🔒 ALWAYS lock before reading/modifying
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        # If already finished → stop
        if payout.status in ["completed", "failed"]:
            return

        # ❌ Max retries reached → fail + refund
        if payout.retry_count >= 3:
            payout.status = "failed"

            LedgerEntry.objects.create(
                merchant=payout.merchant,
                type="credit",
                amount_paise=payout.amount_paise
            )

            payout.retry_count += 1
            payout.last_attempt_at = timezone.now()
            payout.save()
            return

        # ⏳ Calculate delay BEFORE releasing lock
        delay = 2 ** payout.retry_count
        payout.retry_count += 1
        payout.last_attempt_at = timezone.now()
        payout.save()

    # ⏳ Sleep OUTSIDE transaction (important)
    time.sleep(delay)

    # 🔁 Retry
    process_payout(payout_id)


def process_payout(payout_id):
    print("🔥 PROCESSOR HIT")

    # 🔒 STEP 1: Move pending → processing
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if payout.status in ["completed", "failed"]:
            return

        if not can_transition(payout.status, "processing"):
            return

        payout.status = "processing"
        payout.last_attempt_at = timezone.now()
        payout.save()

    # 🎲 Simulate bank result (outside lock)
    r = random.random()

    if r < 0.7:
        new_status = "completed"

    elif r < 0.9:
        new_status = "failed"

    else:
        # ⏳ retry instead of stuck
        retry_payout(payout_id)
        return

    # 🔥 STEP 2: Final transition + refund (atomic)
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if not can_transition(payout.status, new_status):
            return

        payout.status = new_status

        # 💰 Refund MUST be inside this block
        if new_status == "failed":
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                type="credit",
                amount_paise=payout.amount_paise
            )

        payout.last_attempt_at = timezone.now()
        payout.save()