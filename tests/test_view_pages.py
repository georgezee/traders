import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_privacy_page_accessible(client):
    """
    Tests that the Privacy policy page is accessible and contains relevant phrases.
    """
    response = client.get("/privacy")
    assert response.status_code == 200
    assert b"privacy policy" in response.content.lower()


@pytest.mark.django_db
def test_terms_page_accessible(client):
    """
    Tests that the Term and conditions page is accessible and contains relevant phrases.
    """
    response = client.get("/terms")
    assert response.status_code == 200
    assert b"terms and conditions" in response.content.lower()
