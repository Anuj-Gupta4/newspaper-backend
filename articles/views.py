from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView, ListAPIView, get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Article, ArticleLike, RSSFeed
from .serializers import ArticleLikesResponseSerializer, ArticleSerializer
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


class ArticleLikeView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ArticleLikesResponseSerializer

    def get_article(self):
        return get_object_or_404(Article, pk=self.kwargs["article_id"])

    def _likes_payload(self, article_id: int, liked: bool) -> dict:
        return {
            "article_id": article_id,
            "likes_count": ArticleLike.objects.filter(article_id=article_id).count(),
            "liked": liked,
        }

    @extend_schema(
        request=None,
        responses={status.HTTP_200_OK: ArticleLikesResponseSerializer},
    )
    def post(self, request, article_id: int):
        article = self.get_article()
        _, created = ArticleLike.objects.get_or_create(user=request.user, article=article)

        return Response(
            {
                "message": "Article liked successfully."
                if created
                else "Article already liked.",
                "data": self._likes_payload(article.id, liked=True),
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={status.HTTP_200_OK: ArticleLikesResponseSerializer},
    )
    def delete(self, request, article_id: int):
        article = self.get_article()
        deleted, _ = ArticleLike.objects.filter(user=request.user, article=article).delete()

        return Response(
            {
                "message": "Article disliked successfully."
                if deleted
                else "Article was not liked.",
                "data": self._likes_payload(article.id, liked=False),
            },
            status=status.HTTP_200_OK,
        )


class ArticleLikesCountView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ArticleLikesResponseSerializer

    @extend_schema(
        responses={status.HTTP_200_OK: ArticleLikesResponseSerializer},
    )
    def get(self, request, article_id: int):
        article = get_object_or_404(Article, pk=article_id)
        likes_count = ArticleLike.objects.filter(article=article).count()

        return Response(
            {
                "message": "Article likes count fetched successfully.",
                "data": {
                    "article_id": article.id,
                    "likes_count": likes_count,
                },
            }
        )

