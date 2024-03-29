"""
This is an adjusted version of the SitemapSpider at:
https://github.com/scrapy/scrapy/blob/master/scrapy/spiders/sitemap.py

The sitemap loc lastmod property is provided in the request meta
"""

import os
import re
import logging
from scrapy.spiders import Spider
from scrapy.http import Request, XmlResponse
from scrapy.utils.sitemap import Sitemap, sitemap_urls_from_robots
from scrapy.utils.gz import gunzip, gzip_magic_number

import soscan.items
import soscan.utils

logger = logging.getLogger(__name__)


class LDSitemapSpider(Spider):
    """
    Provides a generic sitemap spider. It handles gzipped and recursion.
    """

    name = "LDSitemapSpider"
    sitemap_urls = ()
    sitemap_rules = [("", "parse")]
    sitemap_follow = [""]
    sitemap_alternate_links = False

    def __init__(self, *a, alt_rules=None, **kw):
        super().__init__(*a, **kw)
        self._cbs = []
        self.logger.debug("ALT_RULES = %s", alt_rules)
        if alt_rules is not None:
            for r, c in alt_rules:
                if isinstance(c, str):
                    c = getattr(self, c)
                self._cbs.append((regex(r), c))
        else:
            for r, c in self.sitemap_rules:
                if isinstance(c, str):
                    c = getattr(self, c)
                self._cbs.append((regex(r), c))
        self._follow = [regex(x) for x in self.sitemap_follow]
        urls = kw.get("sitemap_urls", None)
        if not urls is None:
            self.sitemap_urls = urls.split(" ")
        # If set, then don't download the target
        self._count_only = kw.get("count_only", False)


    def start_requests(self):
        for url in self.sitemap_urls:
            yield Request(url, self._parse_sitemap)

    def sitemap_filter(self, entries):
        """This method can be used to filter sitemap entries by their
        attributes, for example, you can filter locs with lastmod greater
        than a given date (see docs).
        """
        for entry in entries:
            yield entry

    #def parse(self, response, **kwargs):
    #    print(f"RESPONSE = {response}")

    def _parse_sitemap(self, response):
        if response.url.endswith("/robots.txt"):
            for url in sitemap_urls_from_robots(response.text, base_url=response.url):
                yield Request(url, callback=self._parse_sitemap)
        else:
            body = self._get_sitemap_body(response)
            if body is None:
                logger.warning(
                    "Ignoring invalid sitemap: %(response)s",
                    {"response": response},
                    extra={"spider": self},
                )
                return

            s = Sitemap(body)
            it = self.sitemap_filter(s)

            if s.type == "sitemapindex":
                for (loc, ts, freq, prio) in iterloc(it, self.sitemap_alternate_links):
                    if any(x.search(loc) for x in self._follow):
                        yield Request(loc, callback=self._parse_sitemap)
            elif s.type == "urlset":
                for (loc, ts, freq, prio) in iterloc(it, self.sitemap_alternate_links):
                    for r, c in self._cbs:
                        if r.search(loc):
                            ts = soscan.utils.parseDatetimeString(ts)
                            if self._count_only:
                                item = soscan.items.SitemapItem()
                                item["source"] = response.url
                                item["time_retrieved"] = soscan.utils.dtnow()
                                item["url"] = loc
                                item["time_loc"] = ts
                                item["changefreq"] = freq
                                item["priority"] = prio
                                logger.debug("Yield item: %s", item)
                                yield item
                            else:
                                req = Request(
                                    loc,
                                    callback=c,
                                    flags=[
                                        self._count_only,
                                    ],
                                )
                                req.meta["loc_timestamp"] = ts
                                req.meta["loc_source"] = response.url
                                req.meta["loc_changefreq"] = freq
                                req.meta["loc_priority"] = prio
                                yield req
                            break

    def _get_sitemap_body(self, response):
        """Return the sitemap body contained in the given response,
        or None if the response is not a sitemap.
        """
        if isinstance(response, XmlResponse):
            return response.body
        elif gzip_magic_number(response):
            return gunzip(response.body)
        # actual gzipped sitemap files are decompressed above ;
        # if we are here (response body is not gzipped)
        # and have a response for .xml.gz,
        # it usually means that it was already gunzipped
        # by HttpCompression middleware,
        # the HTTP response being sent with "Content-Encoding: gzip"
        # without actually being a .xml.gz file in the first place,
        # merely XML gzip-compressed on the fly,
        # in other word, here, we have plain XML
        elif response.url.endswith(".xml") or response.url.endswith(".xml.gz"):
            return response.body


def regex(x):
    if isinstance(x, str):
        return re.compile(x)
    return x


def iterloc(it, alt=False):
    for d in it:
        ts = d.get("lastmod", None)
        freq = d.get("changefreq", None)
        prio = d.get("priority", None)
        yield (d["loc"], ts, freq, prio)

        # Also consider alternate URLs (xhtml:link rel="alternate")
        if alt and "alternate" in d:
            yield from (d["alternate"], ts, freq, prio)
