import json
import logging
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from scrapy.http import Request
from scrapy.spiders import Spider

import soscan.items
import soscan.utils


logger = logging.getLogger(__name__)


def extract_path(data, path, default=None):
    """
    Resolve a dotted path against a dict/list structure.

    Examples:
        items
        payload.results
        feed.0
        feed.0.jsonld
    """
    if path in (None, "", "."):
        return data
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (TypeError, ValueError, IndexError):
                return default
            continue
        if isinstance(current, dict):
            if part not in current:
                return default
            current = current[part]
            continue
        return default
    return current


class APIJsonldSpider(Spider):
    """
    Crawl an API that returns paginated JSON with embedded JSON-LD dataset records.

    The spider emits the same `SoscanItem` fields used by the existing pipelines,
    so normalization and persistence continue to work unchanged.
    """

    name = "APIJsonldSpider"
    sitemap_urls = ()
    api_records_path = "items"
    api_next_path = "next"
    api_jsonld_field = None
    api_url_field = "url"
    api_modified_field = None
    api_page_param = None
    api_start_page = 1
    api_success_status_codes = (200,)
    api_stop_status_codes = (204, 404, 410)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._count_only = kwargs.get("count_only", False)
        self.lastmod_filter = kwargs.get("lastmod_filter", kwargs.get("lastmod", None))
        if self.lastmod_filter is not None:
            self.lastmod_filter = soscan.utils.parseDatetimeString(self.lastmod_filter)

        node_path = kwargs.get("store_path", None)
        if node_path is not None:
            node_settings = Path(node_path) / "node.json"
            if node_settings.exists():
                with open(node_settings) as src:
                    node_config = json.loads(src.read())
                self.sitemap_urls = node_config.get("spider", {}).get("sitemap_urls", self.sitemap_urls)

        urls = kwargs.get("sitemap_urls", None)
        if urls is None:
            urls = kwargs.get("api_urls", None)
        if urls is not None:
            if isinstance(urls, str):
                self.sitemap_urls = [u for u in urls.split(" ") if u]
            else:
                self.sitemap_urls = list(urls)

        self.api_records_path = kwargs.get("api_records_path", self.api_records_path)
        self.api_next_path = kwargs.get("api_next_path", self.api_next_path)
        self.api_jsonld_field = kwargs.get("api_jsonld_field", self.api_jsonld_field)
        self.api_url_field = kwargs.get("api_url_field", self.api_url_field)
        self.api_modified_field = kwargs.get("api_modified_field", self.api_modified_field)
        self.api_page_param = kwargs.get("api_page_param", self.api_page_param)
        self.api_start_page = int(kwargs.get("api_start_page", self.api_start_page))
        self.api_success_status_codes = tuple(
            kwargs.get("api_success_status_codes", self.api_success_status_codes)
        )
        self.api_stop_status_codes = tuple(
            kwargs.get("api_stop_status_codes", self.api_stop_status_codes)
        )

        if len(self.sitemap_urls) < 1:
            raise ValueError("At least one sitemap URL is required.")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        node_path = crawler.settings.get("STORE_PATH", None)
        kwargs["store_path"] = node_path
        settings_override = {}
        if node_path is not None:
            mn_settings = Path(node_path) / "settings.json"
            if mn_settings.exists():
                with open(mn_settings) as src:
                    settings_override = json.loads(src.read())
                for key in (
                    "api_records_path",
                    "api_next_path",
                    "api_jsonld_field",
                    "api_url_field",
                    "api_modified_field",
                    "api_page_param",
                    "api_start_page",
                    "api_success_status_codes",
                    "api_stop_status_codes",
                    "lastmod_filter",
                ):
                    if key in settings_override:
                        kwargs[key] = settings_override[key]
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        for key, value in settings_override.items():
            spider.settings.set(key, value, priority="spider")
        return spider

    def start_requests(self):
        headers = {"Accept": "application/ld+json, application/json;q=0.9, */*;q=0.1"}
        for url in self.sitemap_urls:
            req_url = url
            req_meta = {"api_base_url": url, "api_page": self.api_start_page}
            if self.api_page_param:
                req_url = self._set_query_param(url, self.api_page_param, self.api_start_page)
            yield Request(
                req_url,
                callback=self.parse_page,
                headers=headers,
                meta={**req_meta, "handle_httpstatus_all": True},
            )

    def _set_query_param(self, url, key, value):
        parts = urlsplit(url)
        params = dict(parse_qsl(parts.query, keep_blank_values=True))
        params[key] = str(value)
        query = urlencode(params)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

    def _load_payload(self, response):
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not decode API response from {response.url}: {exc}") from exc

    def _normalize_url(self, response, value, default=None):
        if value in (None, ""):
            return default
        return response.urljoin(value)

    def _record_timestamp(self, record):
        if self.api_modified_field is None:
            return None
        return soscan.utils.parseDatetimeString(
            extract_path(record, self.api_modified_field, None)
        )

    def _record_to_item(self, response, record, top_context=None):
        if not isinstance(record, dict):
            logger.warning("Ignoring non-object record from %s: %r", response.url, record)
            return None

        time_loc = self._record_timestamp(record)
        if self.lastmod_filter is not None and time_loc is not None:
            if time_loc <= self.lastmod_filter:
                self.logger.debug(
                    "Skipping API record older than filter: %s <= %s",
                    time_loc,
                    self.lastmod_filter,
                )
                return None

        record_url = self._normalize_url(
            response,
            extract_path(record, self.api_url_field, None),
            default=response.url,
        )

        if self._count_only:
            item = soscan.items.SitemapItem()
            item["source"] = response.url
            item["time_retrieved"] = soscan.utils.dtnow()
            item["url"] = record_url
            item["time_loc"] = time_loc
            item["changefreq"] = None
            item["priority"] = None
            return item

        jsonld = extract_path(record, self.api_jsonld_field, record)
        if jsonld is None:
            logger.warning(
                "Ignoring API record without JSON-LD at %s using field %s",
                response.url,
                self.api_jsonld_field,
            )
            return None
        # Propagate the top-level @context if the record has none of its own.
        # This is common in ItemList APIs (e.g. schema.org) where @context
        # is placed once on the envelope rather than on each Dataset.
        if isinstance(jsonld, dict) and "@context" not in jsonld and top_context is not None:
            jsonld = {"@context": top_context, **jsonld}

        item = soscan.items.SoscanItem()
        item["url"] = record_url
        item["status"] = response.status
        item["time_loc"] = time_loc
        item["time_modified"] = None
        item["time_retrieved"] = soscan.utils.dtnow()
        item["jsonld"] = jsonld
        return item

    def _next_request(self, response, payload, record_count):
        next_url = extract_path(payload, self.api_next_path, None)
        next_url = self._normalize_url(response, next_url)
        if next_url not in (None, response.url):
            headers = {"Accept": "application/ld+json, application/json;q=0.9, */*;q=0.1"}
            return Request(
                next_url,
                callback=self.parse_page,
                headers=headers,
                meta={"handle_httpstatus_all": True},
            )

        if not self.api_page_param:
            return None

        if response.status in self.api_stop_status_codes:
            self.logger.info("Stopping API pagination at status %s for %s", response.status, response.url)
            return None

        if response.status not in self.api_success_status_codes:
            self.logger.warning(
                "Stopping API pagination due to non-success status %s at %s",
                response.status,
                response.url,
            )
            return None

        if record_count < 1:
            self.logger.info("Stopping API pagination due to empty page at %s", response.url)
            return None

        current_page = int(response.meta.get("api_page", self.api_start_page))
        next_page = current_page + 1
        base_url = response.meta.get("api_base_url", response.url)
        next_url = self._set_query_param(base_url, self.api_page_param, next_page)
        headers = {"Accept": "application/ld+json, application/json;q=0.9, */*;q=0.1"}
        return Request(
            next_url,
            callback=self.parse_page,
            headers=headers,
            meta={
                "api_base_url": base_url,
                "api_page": next_page,
                "handle_httpstatus_all": True,
            },
        )

    def parse_page(self, response):
        if response.status in self.api_stop_status_codes:
            self.logger.info(
                "Received stop status %s at %s; finishing crawl chain.",
                response.status,
                response.url,
            )
            return
        if response.status not in self.api_success_status_codes:
            self.logger.warning(
                "Ignoring unexpected status %s at %s",
                response.status,
                response.url,
            )
            return

        payload = self._load_payload(response)
        records = extract_path(payload, self.api_records_path, [])
        if isinstance(records, dict):
            records = [records]
        elif records is None:
            records = []
        elif not isinstance(records, list):
            raise ValueError(
                f"API records path {self.api_records_path} did not resolve to a list or object: {type(records)}"
            )

        record_count = len(records)

        # Capture any top-level @context so it can be injected into records
        # that don't carry their own (e.g. schema.org ItemList APIs).
        top_context = payload.get("@context", None)

        yielded_count = 0
        for record in records:
            item = self._record_to_item(response, record, top_context=top_context)
            if item is not None:
                yielded_count += 1
                yield item

        self.logger.info(
            "Processed %s API records (%s items yielded) from %s",
            record_count,
            yielded_count,
            response.url,
        )
        next_request = self._next_request(response, payload, record_count)
        if next_request is not None:
            yield next_request