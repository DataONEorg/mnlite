import os
import sonormal
import pyld
import email.utils
import json
import dateparser
import soscan.spiders.ldsitemapspider
import soscan.items
import opersist.utils
import opersist.rdfutils
from scrapy.utils.project import get_project_settings


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
                settings_file: JSON node config file
        """
        super(JsonldSpider, self).__init__(*args, **kwargs)

        sonormal.installDocumentLoader(expire_existing=False)

        node_settings = None
        node_path = kwargs.get("store_path", None)
        if not node_path is None:
            node_settings = os.path.join(node_path, "node.json")
        node_settings = kwargs.get("settings_file", node_settings)
        if node_settings is not None:
            if os.path.exists(node_settings):
                _data = {}
                with open(node_settings) as src:
                    _data = json.load(src)
                self.sitemap_urls = _data.get("spider",{}).get("sitemap_urls", None)
        urls = kwargs.get("sitemap_urls", None)
        if not urls is None:
            self.sitemap_urls = urls.split(" ")
        self.lastmod_filter = kwargs.get("lastmod", None)
        if len(self.sitemap_urls) < 1:
            raise ValueError("At least one sitemap URL is required.")
        if self.lastmod_filter is not None:
            self.lastmod_filter = dateparser.parse(
                self.lastmod_filter, settings={"RETURN_AS_TIMEZONE_AWARE": True}
            )
        #If set, then don't download the target
        self._count_only = kwargs.get("count_only", False)


    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        node_path=crawler.settings.get("STORE_PATH", None)
        alt_rules = None
        if not node_path is None:
            node_settings = os.path.join(node_path, "node.json")
            if os.path.exists(node_settings):
                _data = {}
                with open(node_settings) as src:
                    _data = json.load(src)
                url_rules = _data.get("spider",{}).get("url_rules", [])
                if len(url_rules) > 0:
                    alt_rules = []
                    for arule in url_rules:
                        alt_rules.append((arule[0], arule[1]))
        spider = cls(
            *args,
            store_path=crawler.settings.get("STORE_PATH", None),
            alt_rules=alt_rules,
            **kwargs
        )
        spider._set_crawler(crawler)
        return spider


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
            #for j_item in jsonld:
            #    item = soscan.items.SoscanItem()
            #    item["source"] = response.url
            #    item["checksum"] = opersist.rdfutils.computeJSONLDChecksum(j_item, response.url)

            if len(jsonld) > 0:
                # These values are set in the opersistpiteline and sonormalizepipeline
                # checksum
                # identifier
                # series_id
                # filename
                # source
                # alt_identifiers
                # format_id

                item = soscan.items.SoscanItem()
                item["url"] = response.url
                item["status"] = response.status
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
                item["time_retrieved"] = opersist.utils.dtnow()
                self.logger.debug("ITEM without jsonld: %s", item)
                item["jsonld"] = jsonld
                yield item
        except Exception as e:
            self.logger.error("parse : %s", e)
        yield None
