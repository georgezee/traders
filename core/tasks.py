import logging

from celery import shared_task
from django.conf import settings

from core.models import Feedback
from core.utils.slack import (
    SlackNotificationError,
    SlackWebhookClient,
    build_feedback_payload,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(SlackNotificationError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_feedback_to_slack(self, feedback_id: int) -> None:
    try:
        feedback = Feedback.objects.get(pk=feedback_id)
    except Feedback.DoesNotExist:
        logger.info("Feedback %s no longer exists; skipping Slack notification.", feedback_id)
        return

    payload = build_feedback_payload(feedback)
    notifier = SlackWebhookClient(settings.SLACK_WEBHOOK_APP_FEEDBACK)

    try:
        notifier.send_message(payload)
        logger.info("Sent Slack notification for Feedback %s", feedback_id)
    except SlackNotificationError as exc:
        logger.warning("Slack notification failed for Feedback %s: %s", feedback_id, exc)
        raise
