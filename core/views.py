import hashlib
import io
from urllib.parse import urlencode, urljoin

import segno
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from rest_framework import generics, permissions
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from core.forms import FeedbackForm, FlagContentForm, FollowForm
from core.models import Feedback
from core.serializers import FeedbackSerializer

# Define a throttle for anonymous feedback.
class FeedbackAnonThrottle(AnonRateThrottle):
    scope = "feedback_anon"

@require_http_methods(["GET", "POST"])
def contact_view(request):
    if request.method == "POST":
        form = FeedbackForm(
            request.POST,
            user=request.user,
            request=request,
            category_choices=Feedback.CONTACT_PAGE_CATEGORY_CHOICES,
        )
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.feedback_type = "Contact"
            if request.user.is_authenticated:
                feedback.user = request.user
            feedback.save()
            messages.success(request, "Thank you for your message!")
            return redirect("contact")
    else:
        form = FeedbackForm(
            user=request.user,
            request=request,
            category_choices=Feedback.CONTACT_PAGE_CATEGORY_CHOICES,
        )

    return render(request, "core/contact.html", {
        "form": form,
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
    })


@require_http_methods(["GET", "POST"])
def contact_modal_view(request):
    is_htmx = request.headers.get("HX-Request") == "true"
    if request.method == "POST":
        form = FeedbackForm(request.POST, user=request.user, request=request)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.feedback_type = "Contact"
            if request.user.is_authenticated:
                feedback.user = request.user
            feedback.save()
            return render(request, "core/modal_success.html", {}, status=200)
    else:
        form = FeedbackForm(user=request.user, request=request)

    if is_htmx:
        modal_url = reverse("contact_modal")
        form.helper.form_action = modal_url
        attrs = dict(form.helper.attrs or {})
        attrs.update({
            "hx-post": modal_url,
            "hx-target": "#modal",
            "hx-swap": "outerHTML",
        })
        form.helper.attrs = attrs

    template = "core/contact_modal_form.html" if is_htmx else "core/contact.html"
    return render(request, template, {
        "form": form,
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
    })


@require_http_methods(["GET", "POST"])
def flag_content_modal_view(request):
    is_htmx = request.headers.get("HX-Request") == "true"
    step_slug = request.GET.get("step") or request.POST.get("target") or ""
    step_title = request.GET.get("title") or request.POST.get("step_title") or ""
    success_message = "Thanks for flagging this step. We'll review it shortly."
    auto_close_delay = 3
    submission_failed = False

    if request.method == "POST":
        form = FlagContentForm(request.POST, user=request.user, request=request)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.feedback_type = "Lesson"
            if request.user.is_authenticated:
                feedback.user = request.user
            if not feedback.target and step_slug:
                feedback.target = step_slug

            context_details = []
            if step_title:
                context_details.append(f"Step title: {step_title}")
            if feedback.target or step_slug:
                context_details.append(f"Step slug: {feedback.target or step_slug}")

            hx_url = request.headers.get("HX-Current-URL") or request.META.get("HTTP_HX_CURRENT_URL")
            referer = request.META.get("HTTP_REFERER")
            absolute_request_url = request.build_absolute_uri()
            page_url = hx_url or referer or absolute_request_url
            if page_url:
                context_details.append(f"Page URL: {page_url}")

            if context_details:
                base_message = (feedback.message or "").rstrip()
                context_block = "\n".join(context_details)
                if base_message:
                    feedback.message = f"{base_message}\n\n---\nContext\n{context_block}"
                else:
                    feedback.message = f"Context\n{context_block}"

            feedback.save()
            if is_htmx:
                return render(request, "core/flag_content_modal_form.html", {
                    "form": None,
                    "step_title": step_title,
                    "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
                    "submission_failed": False,
                    "submission_success": True,
                    "success_message": success_message,
                    "auto_close_delay": auto_close_delay,
                }, status=200)
            return render(request, "core/modal_success.html", {
                "message": success_message,
            }, status=200)
        submission_failed = True
    else:
        form = FlagContentForm(
            user=request.user,
            request=request,
            initial={
                "target": step_slug,
            }
        )

    if is_htmx:
        query_params = {}
        if step_slug:
            query_params["step"] = step_slug
        if step_title:
            query_params["title"] = step_title
        modal_url = reverse("flag_content_modal")
        if query_params:
            modal_url = f"{modal_url}?{urlencode(query_params)}"
        form.helper.form_action = modal_url
        attrs = dict(form.helper.attrs or {})
        attrs.update({
            "hx-post": modal_url,
            "hx-target": "#modal",
            "hx-swap": "outerHTML",
        })
        form.helper.attrs = attrs

    template = "core/flag_content_modal_form.html" if is_htmx else "core/contact.html"
    return render(request, template, {
        "form": form,
        "step_title": step_title,
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
        "submission_failed": submission_failed,
        "submission_success": False,
        "success_message": success_message,
        "auto_close_delay": auto_close_delay,
    })

@require_http_methods(["GET", "POST"])
def follow_view(request):
    if request.method == "POST":
        form = FollowForm(request.POST, user=request.user, request=request)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.feedback_type = "Follow"
            feedback.feedback_category = "Follow"
            if request.user.is_authenticated:
                feedback.user = request.user
            feedback.save()
            messages.success(request, "Thanks for following Traders! We'll keep you updated.")
            return redirect("follow")
    else:
        form = FollowForm(user=request.user, request=request)

    return render(request, "core/follow.html", {
        "form": form,
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
    })

def _cache_get(key):
    try:
        return cache.get(key)
    except DatabaseError:
        return None


def _cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout=timeout)
    except DatabaseError:
        return


@require_GET
def qr_view(request, target_path: str = ""):
    base_url = settings.QR_CODE_BASE_URL.rstrip("/") + "/"
    normalized_path = target_path.strip("/")
    target_url = urljoin(base_url, normalized_path) if normalized_path else base_url.rstrip("/")

    cache_key = f"qr:{hashlib.sha256(target_url.encode('utf-8')).hexdigest()}"
    qr_bytes = _cache_get(cache_key)

    if qr_bytes is None:
        qr = segno.make(target_url, **settings.SEGNO_DEFAULTS)
        buffer = io.BytesIO()
        qr.save(buffer, kind="png", scale=settings.QR_CODE_SCALE)
        qr_bytes = buffer.getvalue()
        _cache_set(cache_key, qr_bytes, settings.QR_CODE_CACHE_TIMEOUT)

    return HttpResponse(qr_bytes, content_type="image/png")


class FeedbackListCreateAPIView(generics.ListCreateAPIView):
    queryset = Feedback.objects.all().order_by("-date_created")
    serializer_class = FeedbackSerializer
    throttle_classes = [UserRateThrottle, FeedbackAnonThrottle]

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]
