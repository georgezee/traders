from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings

from core.forms import FeedbackForm


@override_settings(TURNSTILE_SECRET_KEY="test-secret", TURNSTILE_SITE_KEY="test-site")
class FeedbackFormTurnstileTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _base_form_data(self):
        return {
            "name": "",
            "feedback_category": "General",
            "message": "Hello Traders",
            "email": "",
        }

    def test_feedback_form_requires_turnstile_token(self):
        request = self.factory.post("/contact/")
        form = FeedbackForm(data=self._base_form_data(), request=request)

        self.assertFalse(form.is_valid())
        self.assertIn("verify", "".join(form.non_field_errors()))

    @patch("core.forms.verify_turnstile", return_value=(True, []))
    def test_feedback_form_accepts_valid_turnstile_token(self, verify_mock):
        request = self.factory.post("/contact/")
        data = self._base_form_data()
        data["turnstile_token"] = "token-value"

        form = FeedbackForm(data=data, request=request)

        self.assertTrue(form.is_valid())
        verify_mock.assert_called_once()

    @patch("core.forms.verify_turnstile", return_value=(True, []))
    def test_feedback_form_accepts_cf_response_token(self, verify_mock):
        request = self.factory.post("/contact/")
        data = self._base_form_data()
        data["cf-turnstile-response"] = "cf-token"

        form = FeedbackForm(data=data, request=request)

        self.assertTrue(form.is_valid())
        verify_mock.assert_called_once()
