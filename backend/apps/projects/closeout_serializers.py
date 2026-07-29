from rest_framework import serializers


class CloseoutDispositionSerializer(serializers.Serializer):
    cancelOpenTasks = serializers.BooleanField(default=False)
    closePendingReports = serializers.BooleanField(default=False)
    cancelOpenBookings = serializers.BooleanField(default=False)
    materialsReviewed = serializers.BooleanField()
    finalPackageConfirmed = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=4000)


class CloseoutCheckSerializer(serializers.Serializer):
    key = serializers.CharField()
    count = serializers.IntegerField()
    severity = serializers.ChoiceField(choices=["clear", "attention", "blocked"])
    sample = serializers.ListField(child=serializers.DictField())


class ProjectCloseoutPreflightSerializer(serializers.Serializer):
    projectId = serializers.IntegerField()
    ready = serializers.BooleanField()
    checks = CloseoutCheckSerializer(many=True)
    latestCloseout = serializers.DictField(allow_null=True)


class ProjectCloseoutResultSerializer(serializers.Serializer):
    projectId = serializers.IntegerField()
    status = serializers.CharField()
    archiveVersion = serializers.IntegerField()
    archivedAt = serializers.DateTimeField()
    checklist = serializers.DictField()
