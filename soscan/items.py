# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
import soscan.utils


def serializeDateTime(dt):
    return soscan.utils.datetimeToJsonStr(dt)


class SitemapItem(scrapy.Item):
    """
    Properties of a sitemap item.

    Items of this type are emitted by the ldsitemapspider instead of
    downloading the item.

    Attributes:
        source: The URL of the source sitemap
        time_retrieved: When the item was found in the sitemap
        url: URL of the item in the sitemap
        time_loc: Timestamp in sitemap lastmod value, if available
        changefreq: String value of the changefreq element, if available
        priority: Value of the priority element, if available
    """

    source = scrapy.Field()
    time_retrieved = scrapy.Field(serializer=serializeDateTime)
    url = scrapy.Field()
    time_loc = scrapy.Field(serializer=serializeDateTime)
    changefreq = scrapy.Field()
    priority = scrapy.Field()


class JsonLDItem(SitemapItem):
    """
    JSON-LD retrieved from a page found by crawling a sitemap.

    Content retrieved from a web page is treated as an RDF dataset, and
    so will always be a list even if only a single JSON-LD block
    is retrieved from the page.

    Attributes:
        elapsed: Seconds taken to retrieve the page
        time_modified: Value of Last-Modified response header, if available
        jsonld: list of JSON-LD structures extracted from a page
    """

    elapsed = scrapy.Field()
    time_modified = scrapy.Field(serializer=serializeDateTime)
    jsonld = scrapy.Field()


class SoscanItem(scrapy.Item):
    """
    Set all the properties on a json-ld thing.

    All properties that need to be preserved in the database etc should be set here
    """

    url = scrapy.Field()
    status = scrapy.Field()  # http status
    time_retrieved = scrapy.Field()
    time_loc = scrapy.Field()  # From the sitemap, if available
    time_modified = scrapy.Field()  # From the HTTP response header, if available
    time_dsmodified = (
        scrapy.Field()
    )  # dateModified value in JSON-LD object, if availale
    jsonld = scrapy.Field()  # The JSON-LD object (de-serialized)
    normalized = scrapy.Field()  # the normalized JSON-LD object
    identifier = scrapy.Field()  # PID to be used for the item
    series_id = scrapy.Field()  # Series ID to be used for the item
    alt_identifiers = scrapy.Field()  # alternative identifiers extracted from the item
    format_id = scrapy.Field()
