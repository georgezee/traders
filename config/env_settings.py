from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings
from pathlib import Path


class DjangoSettings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

    base_dir: Path = Path(__file__).resolve().parent.parent
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(..., alias="SECRET_KEY")
    sentry_url: str = Field(..., alias="SENTRY_URL")
    allowed_hosts_raw: str = Field(default="localhost", alias="DJANGO_ALLOWED_HOSTS")
    paystack_public_key: str = Field(..., alias="PAYSTACK_PUBLIC_KEY")
    paystack_secret_key: str = Field(..., alias="PAYSTACK_SECRET_KEY")
    smtp_host: str = Field(..., alias="SMTP_HOST")
    smtp_host_user: str = Field(..., alias="SMTP_HOST_USER")
    smtp_host_password: str = Field(..., alias="SMTP_HOST_PASSWORD")
    google_client_id: str = Field(..., alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., alias="GOOGLE_CLIENT_SECRET")
    default_contact_email: str = Field(..., alias="DEFAULT_CONTACT_EMAIL")
    content_repository_url: str = Field(..., alias="CONTENT_REPOSITORY_URL")
    content_local_path: str = Field(..., alias="CONTENT_LOCAL_PATH")
    turnstile_site_key: str = Field("", alias="TURNSTILE_SITE_KEY")
    turnstile_secret_key: str = Field("", alias="TURNSTILE_SECRET_KEY")
    celery_broker_url: str = Field("redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")
    slack_webhook_app_feedback: str = Field("", alias="SLACK_WEBHOOK_APP_FEEDBACK")
    base_url: str = Field("https://example.com", alias="BASE_URL")

    @property
    def allowed_hosts(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts_raw.split(",")]

settings = DjangoSettings()
