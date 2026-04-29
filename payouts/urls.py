from django.urls import path
from django.http import JsonResponse
from .views import create_payout, get_balance_view, get_payout_status


def test_api(request):
    return JsonResponse({"message": "API working 🚀"})


urlpatterns = [
    path("", test_api),  # GET /api/v1/
    path("payouts/<int:merchant_id>/", create_payout),  # POST
    path("balance/<int:merchant_id>/", get_balance_view),  # GET
    path("payout-status/<int:payout_id>/", get_payout_status),
]