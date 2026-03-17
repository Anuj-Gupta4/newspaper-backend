from django.contrib import admin

from .models import Article, ArticleLike, RSSFeed, Tag


@admin.register(RSSFeed)
class RSSFeedAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "url", "is_active", "last_fetched_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "url")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "feed", "published_at", "author")
    list_filter = ("feed", "published_at")
    search_fields = ("title", "summary", "content", "author")
    date_hierarchy = "published_at"
    raw_id_fields = ("feed", "tags")


@admin.register(ArticleLike)
class ArticleLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "article", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "article__title")

from django.contrib import admin

# Register your models here.
