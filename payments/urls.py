from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.contribute, name="contribute"),
    path("checkout/", views.contribute_checkout, name="contribute_checkout"),
    path("callback/", views.contribute_callback, name="contribute_callback"),
    path("webhook/", views.paystack_webhook, name="paystack_webhook"),
]
