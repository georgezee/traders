import logging

from django import forms
from django.conf import settings
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, HTML, Layout, Submit
from core.models import Feedback
from core.turnstile import verify_turnstile


logger = logging.getLogger(__name__)


class TurnstileFormMixin:
    """Shared behavior for forms protected by Cloudflare Turnstile."""

    turnstile_token = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if self._errors:
            return cleaned_data

        token_field_value = cleaned_data.get("turnstile_token")
        cf_response = self.data.get("cf-turnstile-response")
        token = token_field_value or cf_response

        logger.debug(
            "Turnstile tokens for %s: hidden_field_present=%s, cf_response_present=%s",
            self.__class__.__name__,
            bool(token_field_value),
            bool(cf_response),
        )

        if not token:
            logger.warning(
                "Turnstile token missing for form %s before verification.",
                self.__class__.__name__,
            )

        verified, error_codes = verify_turnstile(token, self._get_remote_ip())

        if not verified:
            logger.warning(
                "Turnstile verification failed for form %s (errors=%s)",
                self.__class__.__name__,
                error_codes,
            )
            self.add_error(None, self._turnstile_error_message(error_codes))

        return cleaned_data

    def _get_remote_ip(self) -> str | None:
        if not self.request:
            return None

        forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return self.request.META.get("REMOTE_ADDR")

    def _turnstile_error_message(self, error_codes):
        error_codes = list(error_codes or [])
        if "timeout-or-duplicate" in error_codes:
            return "The verification expired. Please try again."
        if "request-error" in error_codes:
            return "We couldn't reach the verification service. Please try again."
        if "missing-secret" in error_codes:
            return "Turnstile has not been configured yet. Please try again later."
        return "We couldn't verify that you're human. Please try again."

    def _initialise_turnstile_helper(self, form_id: str):
        if not hasattr(self, "helper"):
            return

        if not getattr(self.helper, "form_id", None):
            self.helper.form_id = form_id

        attrs = dict(getattr(self.helper, "attrs", {}) or {})
        attrs.setdefault("data-requires-turnstile", "true")
        attrs["data-turnstile-sitekey"] = getattr(settings, "TURNSTILE_SITE_KEY", "")
        attrs.setdefault("data-turnstile-mode", "managed")
        self.helper.attrs = attrs
        self.helper.render_hidden_fields = True


class FeedbackForm(TurnstileFormMixin, forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["name", "email", "phone", "feedback_category", "message"]
        labels = {
            "name": "Your name",
            "email": "Email address",
            "phone": "Phone number",
            "feedback_category": "How can we help?",
            "message": "Tell us what you need",
        }

    def __init__(self, *args, **kwargs):
        category_choices = kwargs.pop("category_choices", Feedback.FEEDBACK_CATEGORY_CHOICES)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Ensure the textarea has a consistent height with the layout
        self.fields["message"].widget.attrs.update({"rows": 4})
        self.fields["feedback_category"].choices = category_choices
        self.fields["phone"].required = False
        self.fields["name"].required = True
        self.fields["email"].required = True
        self.fields["feedback_category"].required = True
        self.fields["message"].required = True

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Field("name"),
            Field("email"),
            Field("phone"),
            Field("feedback_category"),
            Field("message"),
            FormActions(
                Submit("submit", "Send", css_class="btn btn-primary"),
                css_class="mt-6 flex justify-end"
            )
        )
        self._initialise_turnstile_helper("feedback-form")

        if user and user.is_authenticated:
            self.fields["email"].initial = user.email


class FollowForm(TurnstileFormMixin, forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["name", "email", "message"]
        labels = {
            "name": "Your name",
            "email": "Your email",
            "message": "How did you hear about Traders? (optional)",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Make message field optional with placeholder
        self.fields["message"].required = False
        self.fields["message"].widget.attrs.update({
            "rows": 3
        })

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Field("name"),
            Field("email"),
            Field("message"),
            FormActions(
                Submit("submit", "Sign up", css_class="btn btn-primary"),
                css_class="mt-6 flex justify-end"
            )
        )
        self._initialise_turnstile_helper("follow-form")


class FlagContentForm(TurnstileFormMixin, forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["name", "email", "feedback_category", "message", "target"]
        labels = {
            "name": "Your name (optional)",
            "email": "Your email (optional)",
            "feedback_category": "Why are you flagging this content?",
            "message": "Anything else we should know?",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["feedback_category"].choices = Feedback.FLAG_CATEGORY_CHOICES
        self.fields["feedback_category"].initial = Feedback.FLAG_CATEGORY_CHOICES[0][0]
        self.fields["message"].required = False
        self.fields["message"].widget.attrs.update({
            "rows": 4,
            "placeholder": "Add extra details that will help our team review this step.",
        })
        self.fields["name"].widget = forms.HiddenInput()
        self.fields["email"].widget.attrs.setdefault(
            "placeholder",
            "Share your email if you'd like a reply to this report."
        )
        self.fields["target"].widget = forms.HiddenInput()

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            HTML("""<input type="hidden" name="step_title" value="{{ step_title|default_if_none:'' }}">"""),
            Field("feedback_category"),
            Field("message"),
            Field("email"),
            FormActions(
                Submit("submit", "Send report", css_class="btn btn-primary"),
                css_class="mt-6 flex justify-end"
            )
        )
        self._initialise_turnstile_helper("flag-content-form")

        if user and user.is_authenticated:
            self.fields["email"].initial = user.email

    def clean_message(self):
        message = self.cleaned_data.get("message", "")
        stripped = message.strip()
        return stripped or "No additional details provided."
