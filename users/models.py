from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """User profile with account-level metadata and extensions."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    # Metadata for conflict resolution - stores timestamps and client op IDs for profile-level data
    metadata = models.JSONField(
        default=dict,
        help_text="Profile-level metadata for conflict resolution"
    )
    points = models.PositiveIntegerField(
        default=0,
        help_text="User points/score (future gamification)"
    )
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    # Placeholders for future features
    # subscription_plan = models.ForeignKey('payments.SubscriptionPlan', ...)
    # team = models.ForeignKey('teams.Team', ...)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        indexes = [
            # GIN index for JSON queries on metadata
            GinIndex(fields=['metadata'], name='users_userprofile_metadata_gin')
        ]

    def __str__(self):
        return f"{self.user.username}'s profile"


class UserPreferences(models.Model):
    """User preferences stored as JSON matching SPA UserPreferences interface."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    data = models.JSONField(
        default=dict,
        help_text="User preferences JSON (autoShift, showMinimap, layoutMode, etc.)"
    )
    # Metadata for conflict resolution - stores per-key timestamps and client op IDs
    metadata = models.JSONField(
        default=dict,
        help_text="Per-key metadata for conflict resolution (updated_at, client_op_id per key)"
    )
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Preferences"
        verbose_name_plural = "User Preferences"
        indexes = [
            # GIN index for JSON queries on both data and metadata
            GinIndex(fields=['data'], name='users_up_data_gin'),
            GinIndex(fields=['metadata'], name='users_up_metadata_gin')
        ]

    def __str__(self):
        return f"{self.user.username}'s preferences"

