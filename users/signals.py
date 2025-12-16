from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, UserPreferences


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile when a User is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Auto-create UserPreferences when a User is created."""
    if created:
        UserPreferences.objects.create(user=instance, data={})


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure UserProfile and UserPreferences exist on user save."""
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    if not hasattr(instance, 'preferences'):
        UserPreferences.objects.create(user=instance, data={})