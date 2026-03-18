from django.urls import path

from .views import ArticleLikeView, ArticleLikesCountView, ArticleListView


urlpatterns = [
    path("articles/", ArticleListView.as_view(), name="article-list"),
    path("articles/<int:article_id>/like/", ArticleLikeView.as_view(), name="article-like"),
    path(
        "articles/<int:article_id>/likes/",
        ArticleLikesCountView.as_view(),
        name="article-likes-count",
    ),
]

