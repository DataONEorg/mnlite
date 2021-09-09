import os
import pytest
import scrapy.http
import mnlite.soscan.spiders.ldsitemapspider
import logging

logging.basicConfig(level=logging.DEBUG)

test_1 = [
    [
        """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>http://www.example.com/foo.html</loc>
    <lastmod>2018-06-04</lastmod>
  </url>
</urlset>""",
        "http://www.example.com/foo.html",
        "2018-06-04"
    ]
]


def fakeXmlResponse(url, src):
    request = scrapy.http.Request(url=url)
    response = scrapy.http.XmlResponse(url, status=200, request=request, body=src, encoding="utf-8")
    return response

@pytest.mark.parametrize("smap,expected_log,expected_lastmod", test_1)
def test_parse(smap, expected_log, expected_lastmod):
    response = fakeXmlResponse("https://example.net/sitemap.xml", smap.encode("utf-8"))
    spider = mnlite.soscan.spiders.ldsitemapspider.LDSitemapSpider(count_only=True)
    for item in spider._parse_sitemap(response):
        print(item)
    pass