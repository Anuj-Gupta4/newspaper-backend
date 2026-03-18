from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from .models import Article, RSSFeed
from .serializers import ArticleSerializer
from .services import sync_all_feeds


class ArticlePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="category",
            type=OpenApiTypes.STR,
            required=False,
            description=(
                "Filter articles by RSS feed category. "
                f"Allowed: {', '.join([c[0] for c in RSSFeed.CATEGORY_CHOICES])}. "
                f"Default: {RSSFeed.WORLD_NEWS}."
            ),
        ),
    ],
)
class ArticleListView(ListAPIView):
    """
    GET /api/articles/

    On request:
    - If the requested category has no stored articles yet, pull the feed once.
    - Otherwise, return articles from the DB without syncing again.
    """

    serializer_class = ArticleSerializer
    pagination_class = ArticlePagination

    def get_queryset(self):
        request = self.request
        category = request.query_params.get("category")

        # Default category if none provided
        if not category:
            category = RSSFeed.WORLD_NEWS

        # Only allow known categories; unknown category returns empty
        allowed = {choice[0] for choice in RSSFeed.CATEGORY_CHOICES}
        if category not in allowed:
            return Article.objects.none()

        queryset = Article.objects.filter(feed__category=category, feed__is_active=True)
        if not queryset.exists():
            sync_all_feeds(categories=[category])
            queryset = Article.objects.filter(feed__category=category, feed__is_active=True)

        return (
            queryset.select_related("feed")
            .prefetch_related("tags")
            .annotate(likes_count=Count("likes"))
        )

