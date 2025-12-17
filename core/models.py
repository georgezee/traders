import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import models


logger = logging.getLogger(__name__)


class Feedback(models.Model):
    FEEDBACK_TYPES = [
        ("Contact", "Contact"),
        ("Follow", "Follow"),
        ("Other", "Other"),
    ]

    FEEDBACK_CATEGORY_CHOICES = [
        ("Feedback", "Feedback"),
        ("Partnership", "Partnerships"),
        ("General", "General enquiry"),
        ("Support", "I need help with something"),
        ("Other", "Something Else"),
        ("flag_incorrect", "Incorrect or outdated information"),
        ("flag_inappropriate", "Inappropriate or unsafe content"),
        ("flag_off_topic", "Off-topic or irrelevant content"),
        ("flag_bug", "Bug or technical issue"),
        ("flag_other", "Other"),
    ]
    CONTACT_PAGE_CATEGORY_CHOICES = [
        ("General", "General enquiry"),
        ("Feedback", "Feedback"),
    ]
    FLAG_CATEGORY_CHOICES = [
        ("flag_incorrect", "Incorrect or outdated information"),
        ("flag_inappropriate", "Inappropriate or unsafe content"),
        ("flag_off_topic", "Off-topic or irrelevant content"),
        ("flag_bug", "Bug or technical issue"),
        ("flag_other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback",
    )
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True, validators=[validate_email])
    phone = models.CharField(max_length=50, blank=True)
    message = models.TextField()
    feedback_type = models.CharField(
        max_length=20, choices=FEEDBACK_TYPES, default="Other"
    )
    feedback_category = models.CharField(
        max_length=20, choices=FEEDBACK_CATEGORY_CHOICES, default="Other", blank=False
    )
    target = models.CharField(max_length=255, blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Feedback"
        verbose_name_plural = "Feedback"
        ordering = ["-date_created"]

    def __str__(self):
        return f"Feedback from {self.name or 'Anonymous'} ({self.feedback_type})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.send_notification_email()
            self.enqueue_slack_notification()

    def send_notification_email(self):
        try:
            subject = f"[Traders] Feedback: {self.feedback_category}"
            from_email = getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                f"noreply@{getattr(settings, 'BASE_DOMAIN', 'example.com')}",
            )
            to_email = [getattr(settings, "DEFAULT_CONTACT_EMAIL", None)]

            if not to_email[0]:
                return  # Don't try to send if no contact email is configured

            message = f"""
New feedback submitted:

Name: {self.name or "Anonymous"}
Email: {self.email or "Not provided"}
Category: {self.feedback_category}
Type: {self.feedback_type}

Message:
{self.message}
""".strip()

            send_mail(subject, message, from_email, to_email)
        except Exception as e:
            logger.warning("Feedback notification email failed: %s", e, exc_info=True)

    def enqueue_slack_notification(self):
        try:
            from core.tasks import send_feedback_to_slack

            if self.pk:
                send_feedback_to_slack.delay(self.pk)
        except Exception as exc:
            logger.warning("Unable to enqueue Slack notification: %s", exc, exc_info=True)
