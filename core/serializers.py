from rest_framework import serializers
from core.models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = [
            "id", "name", "email", "message", "feedback_type", "feedback_category",
            "target", "date_created"
        ]
        read_only_fields = ["feedback_type", "date_created"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        validated_data["feedback_type"] = "Contact"  # or infer if needed
        return super().create(validated_data)
