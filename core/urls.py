from django.contrib import admin
from django.urls import path

from payouts.views import LedgerListView, MerchantBalanceView, PayoutListCreateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/v1/merchants/<int:merchant_id>/balance",
        MerchantBalanceView.as_view(),
        name="merchant-balance",
    ),
    path("api/v1/payouts", PayoutListCreateView.as_view(), name="payouts"),
    path("api/v1/ledger", LedgerListView.as_view(), name="ledger"),
]
