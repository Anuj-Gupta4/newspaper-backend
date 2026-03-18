from rest_framework import serializers

from .models import Article, RSSFeed, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class RSSFeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSSFeed
        fields = ["id", "name", "url", "category"]


class ArticleSerializer(serializers.ModelSerializer):
    feed = RSSFeedSerializer(read_only=True)
    feed_category = serializers.CharField(source="feed.category", read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "content",
            "url",
            "image_url",
            "author",
            "language",
            "published_at",
            "fetched_at",
            "feed",
            "feed_category",
            "tags",
            "likes_count",
        ]

