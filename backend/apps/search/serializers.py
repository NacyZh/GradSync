from rest_framework import serializers


class GlobalSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=100, trim_whitespace=True)
    limit = serializers.IntegerField(min_value=1, max_value=10, default=5)


class GlobalSearchResultSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(
        choices=["project", "task", "report", "paper", "document", "code", "member"]
    )
    title = serializers.CharField()
    context = serializers.CharField()
    path = serializers.CharField()
    projectId = serializers.IntegerField(allow_null=True)


class GlobalSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    results = GlobalSearchResultSerializer(many=True)
    counts = serializers.DictField(child=serializers.IntegerField())
