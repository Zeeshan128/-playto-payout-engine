from django.db.models import Sum, Case, When, F, IntegerField
from .models import LedgerEntry

def get_balance(merchant):
    result = LedgerEntry.objects.filter(merchant=merchant).aggregate(
        balance=Sum(
            Case(
                When(type="credit", then=F("amount_paise")),
                When(type="debit", then=-F("amount_paise")),
                output_field=IntegerField(),
            )
        )
    )
    return result["balance"] or 0