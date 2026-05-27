from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.9
    changefreq = 'weekly'

    def items(self):
        # Nombres de las rutas (name) que queremos indexar
        return ['landing:home', 'account_login', 'account_signup']

    def location(self, item):
        return reverse(item)
