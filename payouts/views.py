from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404

from .processor import process_payout
from .models import Merchant, Payout, LedgerEntry
from .services import get_balance


@api_view(["POST"])
def create_payout(request, merchant_id):
    idempotency_key = request.headers.get("Idempotency-Key")
    amount = request.data.get("amount_paise")

    # ✅ Validation
    if not idempotency_key:
        return Response({"error": "Idempotency-Key required"}, status=400)

    if amount is None:
        return Response({"error": "amount_paise required"}, status=400)

    try:
        amount = int(amount)
        if amount <= 0:
            return Response({"error": "Amount must be positive"}, status=400)
    except ValueError:
        return Response({"error": "Invalid amount"}, status=400)

    merchant = get_object_or_404(Merchant, id=merchant_id)

    # 🔁 Idempotency check
    existing = Payout.objects.filter(
        merchant=merchant,
        idempotency_key=idempotency_key
    ).first()

    if existing:
        return Response({
            "id": existing.id,
            "status": existing.status
        })

    # 👉 create payout safely
    with transaction.atomic():
        merchant = Merchant.objects.select_for_update().get(id=merchant_id)

        balance = get_balance(merchant)

        if balance < amount:
            return Response({"error": "Insufficient balance"}, status=400)

        payout = Payout.objects.create(
            merchant=merchant,
            amount_paise=amount,
            idempotency_key=idempotency_key
        )

        # Hold funds
        LedgerEntry.objects.create(
            merchant=merchant,
            type="debit",
            amount_paise=amount
        )

    # 🔥 Run AFTER commit
    import threading

    threading.Thread(target=process_payout, args=(payout.id,)).start()

    # Optional: fetch latest status (since processor may update it)
    payout.refresh_from_db()

    return Response({
        "id": payout.id,
        "status": payout.status
    })
@api_view(["GET"])
def get_balance_view(request, merchant_id):
    merchant = Merchant.objects.get(id=merchant_id)
    balance = get_balance(merchant)

    return Response({
        "merchant_id": merchant_id,
        "balance_paise": balance
    })
from django.shortcuts import get_object_or_404

@api_view(["GET"])
def get_payout_status(request, payout_id):
    payout = get_object_or_404(Payout, id=payout_id)
    return Response({
        "id": payout.id,
        "status": payout.status
    })