import logging
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

from core.models import Feedback

logger = logging.getLogger(__name__)


class SlackNotificationError(Exception):
    """Raised when Slack rejects a webhook payload."""


class SlackWebhookClient:
    def __init__(self, webhook_url: str | None, timeout: int = 5) -> None:
        self.webhook_url = webhook_url or ""
        self.timeout = timeout

    def send_message(self, payload: dict[str, Any]) -> bool:
        """
        Sends a payload to the configured Slack webhook.

        Returns True if the payload was accepted, False if Slack is disabled.
        Raises SlackNotificationError if the HTTP request fails.
        """
        if not self.webhook_url:
            logger.info("Slack webhook not configured; skipping payload.")
            return False

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SlackNotificationError("Slack request failed") from exc

        if response.status_code >= 400:
            raise SlackNotificationError(
                f"Slack webhook returned {response.status_code}: {response.text}"
            )

        return True


def build_feedback_payload(feedback: Feedback) -> dict[str, Any]:
    """
    Build a Slack Block Kit payload for a Feedback instance.
    """
    submitted_at = timezone.localtime(feedback.date_created).strftime(
        "%Y-%m-%d %H:%M %Z"
    )
    feedback_type = feedback.get_feedback_type_display()
    fallback = f"{feedback_type} feedback received"
    message = feedback.message.strip() or "_No message provided._"
    quoted_message = "> " + "\n> ".join(message.splitlines())
    admin_url = build_feedback_admin_url(feedback)

    fields = [
        {
            "type": "mrkdwn",
            "text": f"*Category*\n{feedback.get_feedback_category_display()}",
        },
        {
            "type": "mrkdwn",
            "text": f"*Target*\n{feedback.target or 'N/A'}",
        },
    ]

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{feedback_type} feedback received",
            },
        },
        {"type": "section", "fields": fields},
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Message*\n{quoted_message}",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Submitted:* {submitted_at}",
                }
            ],
        },
    ]

    if admin_url:
        blocks.insert(
            3,
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View"},
                        "url": admin_url,
                    }
                ],
            },
        )

    payload = {
        "text": fallback,
        "blocks": blocks,
    }

    return payload


def build_feedback_admin_url(feedback: Feedback) -> str:
    """
    Construct an absolute admin URL for the feedback entry.
    """
    base_url = getattr(
        settings,
        "BASE_URL",
        f"https://{getattr(settings, 'BASE_DOMAIN', 'example.com')}",
    )

    base_url = base_url.rstrip("/")
    admin_path = settings.ADMIN_URL.strip("/")
    return f"{base_url}/{admin_path}/core/feedback/{feedback.pk}/change/"
