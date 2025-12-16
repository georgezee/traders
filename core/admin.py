from django.contrib import admin
from core.models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message_summary",
        "user",
        "name",
        "email",
        "feedback_type",
        "feedback_category",
        "date_created",
    )
    list_filter = ("feedback_type", "feedback_category", "date_created")
    search_fields = ("message", "name", "email", "target")
    readonly_fields = ("date_created", "date_updated")
    ordering = ("-date_created",)

    def message_summary(self, obj):
        return (obj.message[:75] + "...") if len(obj.message) > 75 else obj.message

    message_summary.short_description = "Message"
