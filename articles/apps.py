from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "articles"

    def ready(self) -> None:
        """
        On startup:
        - Ensure a default set of RSSFeed rows exist.
        - Do not auto-sync articles; article fetches happen lazily on first request.
        """
        try:
            from .models import RSSFeed
        except Exception:
            # Avoid breaking migrations / startup if imports fail.
            return

        try:
            default_feeds = [
                {
                    "name": "BBC Sport",
                    "url": "https://feeds.bbci.co.uk/sport/rss.xml",
                    "category": RSSFeed.SPORTS,
                },
                {
                    "name": "CNN World",
                    "url": "http://rss.cnn.com/rss/edition.rss",
                    "category": RSSFeed.WORLD_NEWS,
                },
                {
                    "name": "Simplecast Feed",
                    "url": "https://feeds.simplecast.com/qm_9xx0g",
                    "category": RSSFeed.OTHER,
                },
                {
                    "name": "OpenAI News",
                    "url": "https://openai.com/news/rss.xml",
                    "category": RSSFeed.AI,
                },
            ]

            for feed in default_feeds:
                RSSFeed.objects.get_or_create(
                    url=feed["url"],
                    defaults={
                        "name": feed["name"],
                        "category": feed["category"],
                        "is_active": True,
                    },
                )

        except Exception:
            # Swallow errors so app can still start; logging can be added later.
            return
