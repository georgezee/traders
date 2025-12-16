from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticPagesSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return [
            "/",
            "/about",
            "/faq",
            "/privacy",
            "/terms",
        ]

    def location(self, item):
        return item


class FeedbackContactSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.3

    def items(self):
        return [
            "/contact/",
        ]

    def location(self, item):
        return item

