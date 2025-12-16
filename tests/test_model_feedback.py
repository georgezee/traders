import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import Feedback


@pytest.mark.django_db
def test_feedback_requires_message():
    with pytest.raises(ValidationError):
        feedback = Feedback()
        feedback.full_clean()  # Should raise because message is required


@pytest.mark.django_db
def test_feedback_optional_fields(end_user):
    feedback = Feedback.objects.create(
        message="This is a test message.",
        name="Test User",
        email="test@example.com",
        user=end_user,
        feedback_type="Contact",
        feedback_category="Support",
        target="lesson-1"
    )
    assert feedback.pk is not None
    assert feedback.name == "Test User"
    assert feedback.email == "test@example.com"
    assert feedback.user == end_user
    assert feedback.feedback_type == "Contact"
    assert feedback.feedback_category == "Support"
    assert feedback.target == "lesson-1"
    assert isinstance(feedback.date_created, timezone.datetime)
    assert isinstance(feedback.date_updated, timezone.datetime)


@pytest.mark.django_db
def test_feedback_email_format_validation():
    feedback = Feedback(
        message="Invalid email test",
        email="not-an-email"
    )
    with pytest.raises(ValidationError):
        feedback.full_clean()


@pytest.mark.django_db
def test_feedback_defaults():
    feedback = Feedback.objects.create(message="Just a message")
    assert feedback.feedback_category == "Other"
    assert feedback.feedback_type == "Other"
    assert feedback.user is None
    assert feedback.name == ""
    assert feedback.email == ""


@pytest.mark.django_db
def test_feedback_ordering(client):
    Feedback.objects.create(message="Old", date_created=timezone.now() - timezone.timedelta(days=1))
    Feedback.objects.create(message="New", date_created=timezone.now())

    feedbacks = Feedback.objects.all()
    assert feedbacks[0].message == "New"
    assert feedbacks[1].message == "Old"
