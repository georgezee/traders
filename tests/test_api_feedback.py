import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Feedback


@pytest.mark.django_db
def test_anonymous_can_submit_feedback():
    client = APIClient()
    url = reverse("feedback-api")
    data = {
        "message": "This is a test message.",
        "email": "test@example.com",
        "name": "Anonymous User",
        "feedback_category": "Other",
    }
    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Feedback.objects.filter(message="This is a test message.").exists()


@pytest.mark.django_db
def test_feedback_requires_message():
    client = APIClient()
    url = reverse("feedback-api")
    response = client.post(url, {"email": "test@example.com"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "message" in response.json()


@pytest.mark.django_db
def test_feedback_with_invalid_email():
    client = APIClient()
    url = reverse("feedback-api")
    response = client.post(url, {"message": "Hi", "email": "not-an-email"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.json()


@pytest.mark.django_db
def test_authenticated_user_feedback_linked(end_user):
    client = APIClient()
    client.force_authenticate(user=end_user)
    url = reverse("feedback-api")
    response = client.post(url, {"message": "Hi from logged in user"}, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    feedback = Feedback.objects.get(message="Hi from logged in user")
    assert feedback.user == end_user


@pytest.mark.django_db
def test_anonymous_user_cannot_list_feedback():
    client = APIClient()
    url = reverse("feedback-api")
    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_staff_user_can_list_feedback(staff_user):
    Feedback.objects.create(message="Visible to staff")
    client = APIClient()
    client.force_authenticate(user=staff_user)
    url = reverse("feedback-api")
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any("Visible to staff" in str(item) for item in data)
