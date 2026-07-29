from rest_framework import serializers


class ProjectHealthSummarySerializer(serializers.Serializer):
    activeProjects = serializers.IntegerField()
    overdueProjects = serializers.IntegerField()
    overdueProjectRate = serializers.FloatField()
    longBlockedTasks = serializers.IntegerField()
    missingReports = serializers.IntegerField()
    governanceHolds = serializers.IntegerField()
    resourceConflicts = serializers.IntegerField()
    notificationFailures = serializers.IntegerField()
    notificationFailureRate = serializers.FloatField()


class ProjectHealthRowSerializer(serializers.Serializer):
    projectId = serializers.IntegerField()
    title = serializers.CharField()
    advisorName = serializers.CharField()
    endsOn = serializers.DateField(allow_null=True)
    overdue = serializers.BooleanField()
    openTaskCount = serializers.IntegerField()
    overdueTaskCount = serializers.IntegerField()
    longBlockedTaskCount = serializers.IntegerField()
    missingReportCount = serializers.IntegerField()
    governanceState = serializers.CharField()
    governanceHoldReason = serializers.CharField()
    resourceConflictCount = serializers.IntegerField()
    notificationFailureCount = serializers.IntegerField()
    healthScore = serializers.IntegerField()
    healthLevel = serializers.ChoiceField(choices=["healthy", "attention", "critical"])
    actionPath = serializers.CharField()


class BlockedTaskHealthSerializer(serializers.Serializer):
    taskId = serializers.IntegerField()
    title = serializers.CharField()
    projectId = serializers.IntegerField()
    projectTitle = serializers.CharField()
    blockedSince = serializers.DateTimeField()
    blockedDays = serializers.IntegerField()
    deadlineAt = serializers.DateTimeField(allow_null=True)
    actionPath = serializers.CharField()


class MissingReportHealthSerializer(serializers.Serializer):
    projectId = serializers.IntegerField()
    projectTitle = serializers.CharField()
    periodId = serializers.IntegerField()
    periodStart = serializers.DateField()
    deadlineAt = serializers.DateTimeField()
    missingCount = serializers.IntegerField()
    actionPath = serializers.CharField()


class GovernanceHoldHealthSerializer(serializers.Serializer):
    projectId = serializers.IntegerField()
    projectTitle = serializers.CharField()
    reason = serializers.CharField()
    startedAt = serializers.DateTimeField(allow_null=True)
    actionPath = serializers.CharField()


class OperationsTrendSerializer(serializers.Serializer):
    date = serializers.DateField()
    resourceConflicts = serializers.IntegerField()
    notificationFailures = serializers.IntegerField()


class ProjectHealthSnapshotSerializer(serializers.Serializer):
    generatedAt = serializers.DateTimeField()
    windowDays = serializers.IntegerField()
    longBlockedDays = serializers.IntegerField()
    summary = ProjectHealthSummarySerializer()
    projects = ProjectHealthRowSerializer(many=True)
    blockedTasks = BlockedTaskHealthSerializer(many=True)
    missingReports = MissingReportHealthSerializer(many=True)
    governanceHolds = GovernanceHoldHealthSerializer(many=True)
    trend = OperationsTrendSerializer(many=True)
