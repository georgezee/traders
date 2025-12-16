import pytest
from django.contrib.auth import get_user_model
from parler.utils.context import switch_language

from core.models import Feedback

@pytest.fixture
def end_user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="password123"
    )

@pytest.fixture
def feedback_item(end_user):
    return Feedback.objects.create(
        message="Example feedback message.",
        name="Test Name",
        email="test@example.com",
        user=end_user,
        feedback_type="Contact",
        feedback_category="General",
        target="lesson-123"
    )

@pytest.fixture
def staff_user(db):
    """Staff user for admin access to API views"""
    User = get_user_model()
    user = User.objects.create_user(
        username="staffuser",
        email="staff@example.com",
        password="testpass123",
        is_staff=True
    )
    return user
