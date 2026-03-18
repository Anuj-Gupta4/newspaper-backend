from articles.models import Article, ArticleLike

# Delete likes first (FK constraint safety)
ArticleLike.objects.all().delete()

# Delete all articles
Article.objects.all().delete()

exit()
