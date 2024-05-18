"""
fname: str,
identifier: str = None,
format_id: str = None,
submitter: str = None,
owner: str = None,
access_rules: list = None,
series_id: str = None,
alt_identifiers: list = None,
media_type: str = None,
source: str = None
"""

import os
import logging
import opersist
import opersist.utils
import sonormal.checksums
import scrapy.exceptions


class OPersistPipeline:
    def __init__(self, fs_path):
        self._op = opersist.OPersist(fs_path)
        self.logger = logging.getLogger("OPersistPipeline")

    @classmethod
    def from_crawler(cls, crawler):
        # db_url = crawler.settings.get("DATABASE_URL", None)
        # return cls(db_url)
        fs_path = crawler.settings.get("STORE_PATH", None)
        if fs_path is None:
            raise Exception("STORE_PATH configuration is required!")
        if not os.path.exists(fs_path):
            raise ValueError(f"STORE_PATH {fs_path} not found.")
        return cls(fs_path)

    def open_spider(self, spider):
        self.logger.debug("open_spider")
        self._op.open(allow_create=True)

    def close_spider(self, spider):
        self.logger.debug("close_spider")
        self._op.close()

    def process_item(self, item, spider):
        try:
            #hashes, _canonical = sonormal.checksums.jsonChecksums(item["normalized"])
            hashes, _canonical = sonormal.checksums.jsonChecksums(item["jsonld"], canonicalize=False)
            checksum_sha256 = hashes.get("sha256", None)
            if checksum_sha256 is None:
                raise scrapy.exceptions.DropItem(f"No checksum for item: {item['url']}")
            existing = self._op.getThingSha256(checksum_sha256)
            if existing is not None:
                raise scrapy.exceptions.DropItem(
                    f"Item already in store:\n{item['url']}\n{checksum_sha256}\n{existing.series_id}\n{existing.file_name}\n==="
                )

            identifier = item["identifier"]
            if identifier is None:
                identifier = f"sha256:{checksum_sha256}"
            format_id = item["format_id"]
            series_id = item.get("series_id", None)  # Set in normalizepipeline
            alt_identifiers = item["alt_identifiers"]
            media_type = "application/ld+json"
            source = item["url"]
            metadata = {
                "http_status": item["status"],
                "time_retrieved": opersist.utils.datetimeToJsonStr(
                    item["time_retrieved"]
                ),
                "time_created": opersist.utils.datetimeToJsonStr(
                    item.get("time_loc", None)
                ),
                "source": item["url"],
            }
            obsoletes = None

            # TODO: Set these values from configuration for the data source
            submitter = None
            owner = None
            access_rules = None

            self.logger.info("Persisting %s", identifier)

            res = self._op.addThingBytes(
                _canonical,
                identifier,
                hashes=hashes,
                format_id=format_id,
                submitter=submitter,
                owner=owner,
                access_rules=access_rules,
                series_id=series_id,
                alt_identifiers=alt_identifiers,
                media_type=media_type,
                source=source,
                metadata=metadata,
                obsoletes=obsoletes,
                date_uploaded=item.get("time_loc", None),
            )

        except Exception as e:
            #self.logger.error(f"{repr(e)}: {e}")
            self.logger.error(f"Exception: {e}")
        return item
