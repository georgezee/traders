"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include

from core.views import (
    FeedbackListCreateAPIView,
    qr_view,
    contact_view,
    contact_modal_view,
    flag_content_modal_view,
    follow_view,
)
from pages.views import home, faq, privacy, terms, about, theme_sample, under_construction

from allauth.account.views import LoginView, LogoutView, SignupView
from django.views.i18n import set_language
from django.views.generic.base import RedirectView
from config.sitemaps import StaticPagesSitemap, FeedbackContactSitemap

def trigger_error(request):
    division_by_zero = 1 / 0
    return division_by_zero


sitemaps = {
    "static": StaticPagesSitemap,
    "feedback": FeedbackContactSitemap,
}

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("i18n/setlang/", set_language, name="set_language"),

    # QR codes
    path("qr", qr_view, name="qr_root"),
    path("qr/<path:target_path>", qr_view, name="qr"),

    # User login and accounts management.
    path('accounts/', include('allauth.urls')),
    # Extra login/logout paths.
    path("login/", LoginView.as_view(), name="account_login_custom"),
    path("logout/", LogoutView.as_view(), name="account_logout_custom"),
    path("signup/", SignupView.as_view(), name="account_signup_custom"),

    # Static pages.
    path("", home, name="home"),
    path("about", about, name="about"),

    path("faq", faq, name="faq"),
    path("privacy", privacy, name="privacy"),
    path("terms", terms, name="terms"),

    # Utility pages.
    path("theme", theme_sample, name="theme_sample"),

    # Feedback / Contact forms.
    path("contact/", contact_view, name="contact"),
    path("follow/", follow_view, name="follow"),

    # Feedback utility paths.
    path("contact/modal/", contact_modal_view, name="contact_modal"),
    path("feedback/flag/", flag_content_modal_view, name="flag_content_modal"),
    path("api/feedback/", FeedbackListCreateAPIView.as_view(), name="feedback-api"),


    # Used to confirm that Sentry is reporting errors correctly.
    path('sentry-debug/', trigger_error),

    # Include all urls from the payments app.
    path("contribute/", include(("payments.urls", "payments"), namespace="payments")),
]