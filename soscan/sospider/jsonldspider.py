import pyld
import email.utils
import dateparser
import soscan.spiders.ldsitemapspider
import soscan.items
import soscan.utils


class JsonldSpider(soscan.spiders.ldsitemapspider.LDSitemapSpider):

    name = "JsonldSpider"

    def __init__(self, *args, **kwargs):
        """
        Extracts JSON-LD from sitemap locations.

        Args:
            *args:
            **kwargs:
                sitemap_urls: space delimited list of sitemap URLs
                lastmod: optional datetime string. Entries equal
                         to or older are excluded.
        """
        super(JsonldSpider, self).__init__(*args, **kwargs)
        urls = kwargs.get("sitemap_urls")
        self.sitemap_urls = urls.split(" ")
        self.lastmod_filter = kwargs.get("lastmod", None)
        if len(self.sitemap_urls) < 1:
            raise ValueError("At least one sitemap URL is required.")
        if self.lastmod_filter is not None:
            self.lastmod_filter = dateparser.parse(
                self.lastmod_filter, settings={"RETURN_AS_TIMEZONE_AWARE": True}
            )

    def sitemap_filter(self, entries):
        """
        Filter loc entries by lastmod time.

        If lastmod_filter is specified for the spider, then
        reject entries that do not have a lastmod value or
        the lastmod value is older than the lastmod_filter value.

        Also converts the entry['lastmod'] value to a
        timezone aware datetime value.

        Args:
            entries: iterator of Sitemap entries

        Returns: None
        """
        for entry in entries:
            ts = entry.get("lastmod", None)
            if not ts is None:
                # convert TS to a datetime for comparison
                ts = dateparser.parse(
                    ts,
                    settings={"RETURN_AS_TIMEZONE_AWARE": True},
                )
                # preserve the converted timestamp in the entry
                entry["lastmod"] = ts

            if self.lastmod_filter is not None and ts is not None:
                if ts > self.lastmod_filter:
                    yield entry
            else:
                yield entry

    def parse(self, response, **kwargs):
        """
        Loads JSON-LD from the response document

        Args:
            response: scrapy response document
            **kwargs:

        Returns: yields the item or None
        """
        try:
            jsonld = pyld.jsonld.load_html(
                response.body, response.url, None, {"extractAllScripts": True}
            )
            if len(jsonld) > 0:
                item = soscan.items.SoscanItem()
                item["url"] = response.url
                item["status"] = response.status
                item["jsonld"] = jsonld
                item["time_loc"] = response.meta["loc_timestamp"]
                item["time_modified"] = None
                response_date = response.headers.get("Last-Modified", None)
                if response_date is not None:
                    try:
                        item["time_modified"] = email.utils.parsedate_to_datetime(
                            response_date.decode()
                        )
                    except Exception as e:
                        self.logger.error(
                            "Could not parse time: %s. %s", response_date, e
                        )
                item["time_retrieved"] = soscan.utils.dtnow()
                yield item
        except Exception as e:
            self.logger.error("parse : %s", e)
        yield None
