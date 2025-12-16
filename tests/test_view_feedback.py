from unittest.mock import patch

import pytest
from django.urls import reverse
from core.models import Feedback


@pytest.mark.django_db
def test_contact_page_loads(client):
    url = reverse("contact")
    response = client.get(url)
    assert response.status_code == 200
    assert b"<form" in response.content
    assert b"name=" in response.content
    assert b"message" in response.content


@pytest.mark.django_db
def test_contact_form_validation_error(client):
    url = reverse("contact")
    response = client.post(url, data={"message": ""})  # blank message
    assert response.status_code == 200
    assert b"This field is required" in response.content or b"error" in response.content.lower()


@pytest.mark.django_db
def test_contact_form_submission_success(client):
    url = reverse("contact")
    response = client.post(url, data={"message": "Hello from test!", "feedback_category": "Other"}, follow=True)
    assert response.status_code == 200
    feedback = Feedback.objects.get(message="Hello from test!")
    assert feedback.feedback_type == "Contact"


@pytest.mark.django_db
def test_htmx_modal_renders_form(client):
    url = reverse("contact_modal")
    response = client.get(url, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert b"<form" in response.content
    assert b"htmx" not in response.content.lower()  # modal shouldn't re-load the whole page


@pytest.mark.django_db
def test_htmx_modal_validation_error(client):
    url = reverse("contact_modal")
    response = client.post(url, data={"message": ""}, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert b"This field is required" in response.content or b"error" in response.content.lower()


@pytest.mark.django_db
def test_htmx_modal_success_closes_modal(client):
    url = reverse("contact_modal")
    response = client.post(
        url,
        data={"message": "HTMX Modal message", "feedback_category": "Other"},
        HTTP_HX_REQUEST="true",
        follow=True
    )
    assert response.status_code == 200
    assert Feedback.objects.filter(message="HTMX Modal message", feedback_category="Other").exists()


@pytest.mark.django_db
def test_flag_modal_renders_form(client):
    url = reverse("flag_content_modal")
    response = client.get(f"{url}?step=test-step&title=Sample", HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert b"Flag this step" in response.content
    assert b"Incorrect or outdated information" in response.content
    assert b'value="test-step"' in response.content


@pytest.mark.django_db
@patch("core.forms.verify_turnstile", return_value=(True, []))
def test_flag_modal_submission_creates_feedback(mock_verify, client):
    url = reverse("flag_content_modal")
    data = {
        "name": "",
        "email": "",
        "feedback_category": "flag_bug",
        "message": "This video will not load.",
        "target": "lesson-42",
        "turnstile_token": "token",
    }
    response = client.post(
        f"{url}?step=lesson-42&title=Debugging",
        data=data,
        HTTP_HX_REQUEST="true"
    )
    assert response.status_code == 200
    feedback = Feedback.objects.get(feedback_category="flag_bug", target="lesson-42")
    assert feedback.feedback_type == "Lesson"
    mock_verify.assert_called_once()
