from django.db.models import Count
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from .models import Article, RSSFeed
from .serializers import ArticleSerializer
from .services import sync_all_feeds


class ArticlePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ArticleListView(ListAPIView):
    """
    GET /api/articles/

    On each request:
    - Pulls latest RSS data into the database (simple sync).
    - Returns a paginated list of articles from the DB.
    """

    serializer_class = ArticleSerializer
    pagination_class = ArticlePagination

    def get_queryset(self):
        request = self.request
        feed_id = request.query_params.get("feed_id")

        feed_ids = None
        queryset = Article.objects.all()

        if feed_id:
            try:
                feed_obj = RSSFeed.objects.get(id=feed_id, is_active=True)
            except RSSFeed.DoesNotExist:
                queryset = queryset.none()
            else:
                feed_ids = [feed_obj.id]
                queryset = queryset.filter(feed=feed_obj)
        else:
            # Default feed: first active feed by name
            default_feed = (
                RSSFeed.objects.filter(is_active=True).order_by("name").first()
            )
            if default_feed is not None:
                feed_ids = [default_feed.id]
                queryset = queryset.filter(feed=default_feed)
            else:
                queryset = queryset.none()

        if feed_ids:
            sync_all_feeds(feed_ids=feed_ids)

        return (
            queryset.select_related("feed")
            .prefetch_related("tags")
            .annotate(likes_count=Count("likes"))
        )

