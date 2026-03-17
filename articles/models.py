from django.conf import settings
from django.db import models
from django.db.models import Count
from django.utils.text import slugify


class RSSFeed(models.Model):
    SPORTS = "sports"
    WORLD_NEWS = "world_news"
    AI = "ai"
    TECH = "tech"
    POLITICS = "politics"
    HEALTH = "health"
    OTHER = "other"

    CATEGORY_CHOICES = [
        (SPORTS, "Sports"),
        (WORLD_NEWS, "World News"),
        (AI, "AI"),
        (TECH, "Tech"),
        (POLITICS, "Politics"),
        (HEALTH, "Health"),
        (OTHER, "Other"),
    ]

    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    category = models.CharField(
        max_length=32,
        choices=CATEGORY_CHOICES,
        default=OTHER,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)

    etag = models.CharField(max_length=255, blank=True)
    last_modified = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "RSS feed"
        verbose_name_plural = "RSS feeds"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_display()})"


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Article(models.Model):
    feed = models.ForeignKey(
        RSSFeed,
        related_name="articles",
        on_delete=models.CASCADE,
    )

    external_id = models.CharField(
        max_length=512,
        help_text="GUID or stable ID from the RSS feed",
    )

    title = models.CharField(max_length=512)
    slug = models.SlugField(max_length=512, blank=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)

    url = models.URLField(help_text="Canonical article URL")
    image_url = models.URLField(blank=True)

    author = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=16, blank=True)

    published_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    tags = models.ManyToManyField(Tag, related_name="articles", blank=True)

    class Meta:
        ordering = ["-published_at"]
        unique_together = ("feed", "external_id")
        indexes = [
            models.Index(fields=["published_at"]),
            models.Index(fields=["feed", "published_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)[:500]
        super().save(*args, **kwargs)


class ArticleLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="article_likes",
        on_delete=models.CASCADE,
    )
    article = models.ForeignKey(
        Article,
        related_name="likes",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "article")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} → {self.article}"
