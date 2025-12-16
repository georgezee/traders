from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
import json

from .models import UserProfile, UserPreferences


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('points', 'date_created', 'date_updated')
    readonly_fields = ('date_created', 'date_updated')


class UserPreferencesInline(admin.StackedInline):
    model = UserPreferences
    can_delete = False
    verbose_name_plural = 'Preferences'
    fields = ('data', 'date_created', 'date_updated')
    readonly_fields = ('date_created', 'date_updated')


# Extend the existing User admin
class ExtendedUserAdmin(UserAdmin):
    inlines = (UserProfileInline, UserPreferencesInline)

# Re-register UserAdmin with our extensions
admin.site.unregister(User)
admin.site.register(User, ExtendedUserAdmin)
