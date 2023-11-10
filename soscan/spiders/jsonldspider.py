import os
from scrapy.settings import BaseSettings
import sonormal
import pyld
import email.utils
from pathlib import Path

try:
    import orjson as json
except ModuleNotFoundError:
    import json

import dateparser
import soscan.spiders.ldsitemapspider
import soscan.items
import opersist.utils
import opersist.rdfutils
from scrapy.utils.project import get_project_settings

# Setup the schema.org contexts for local retrieval
sonormal.prepareSchemaOrgLocalContexts()

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
        kwargs.setdefault("count_only", False)
        super(JsonldSpider, self).__init__(*args, **kwargs)

        node_settings = None
        node_path = kwargs.get("store_path", None)
        if not node_path is None:
            node_settings = os.path.join(node_path, "node.json")
        node_settings = kwargs.get("settings_file", node_settings)
        if node_settings is not None:
            if os.path.exists(node_settings):
                _data = {}
                with open(node_settings) as src:
                    _data = json.loads(src.read())
                self.sitemap_urls = _data.get("spider", {}).get("sitemap_urls", None)
        urls = kwargs.get("sitemap_urls", None)
        if not urls is None:
            self.sitemap_urls = urls.split(" ")
        self.lastmod_filter = kwargs.get("lastmod", None)
        self.start_point = kwargs.get("start_point", None)
        if len(self.sitemap_urls) < 1:
            raise ValueError("At least one sitemap URL is required.")
        if self.lastmod_filter is not None:
            self.lastmod_filter = dateparser.parse(
                self.lastmod_filter, settings={"RETURN_AS_TIMEZONE_AWARE": True}
            )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        node_path = crawler.settings.get("STORE_PATH", None)
        alt_rules = None
        if not node_path is None:
            node_settings = os.path.join(node_path, "node.json")
            if os.path.exists(node_settings):
                _data = {}
                with open(node_settings) as src:
                    _data = json.loads(src.read())
                url_rules = _data.get("spider", {}).get("url_rules", [])
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
        # incorporate MN-specific settings
        mn_settings = Path(f'{node_path}/settings.json')
        if mn_settings.exists():
            with open(mn_settings) as cs:
                _cs = json.loads(cs.read())
            for s in _cs:
                spider.settings.set(s, _cs[s], priority='spider')
                spider.logger.info(f'Setting override from {mn_settings}: set {s} to {_cs[s]}')
                if s in "lastmod_filter":
                    spider.lastmod_filter = dateparser.parse(
                        _cs[s],
                        settings={"RETURN_AS_TIMEZONE_AWARE": True},
                    )
                if s in "start_point":
                    spider.start_point = _cs.get(s, None)
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
        i = 0
        for entry in entries:
            i += 1
            if ((self.start_point is not None) and (self.start_point <= i)) or (self.start_point is None):
                if self.start_point == i:
                    self.logger.info(f'Starting scrape at record {i}')
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
                        self.logger.debug(f'Yielding record {i}: (ts {ts}) {entry}')
                        yield entry
                    else:
                        self.logger.debug(f'lastmod_filter skipping record {i}: (ts {ts}) {entry}')
                else:
                    yield entry
            if (self.start_point is not None) and (self.start_point > i):
                if i == 1:
                    self.logger.info(f'Skipping to start_point at record {self.start_point}')
                self.logger.debug(f'start_point skipping record {i}: {entry}')

    def parse(self, response, **kwargs):
        """
        Loads JSON-LD from the response document

        Args:
            response: scrapy response document
            **kwargs:

        Returns: yields the item or None
        """
        # TODO: set this from configuration
        json_parse_strict = False
        if response.flags is not None:
            if len(response.flags) > 0:
                if response.flags[0]:
                    self.logger.info("Count only: %s", response.url)
                    return
        try:
            options = {
                "extractAllScripts": True,
                "json_parse_strict": json_parse_strict,
            }
            contenttype = response.headers.get("Content-Type").decode()
            #self.logger.debug(f'Response Content-Type: {contenttype} from {response.url}')
            if contenttype in ["application/ld+json", "application/octet-stream"]:
                self.logger.debug(f'Content-Type is "{contenttype}"; assuming json object and loading directly')
                jsonld = json.loads(response.text, strict=options.get("json_parse_strict", False))
            else:
                jsonld = pyld.jsonld.load_html(response.body, response.url, None, options)
            # for j_item in jsonld:
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
                if len(jsonld) == 1:
                    jsonld=jsonld[0]

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
            self.logger.error("parse: url:  %s, %s: %s", response.url, repr(e), e)
        yield None
