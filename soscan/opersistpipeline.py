
'''
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
'''

import logging
import opersist
import opersist.utils

class OPersistPipeline:
    def __init__(self):
        #TODO: config this
        fs_path = "instance/nodes/mn_1"
        self._op = opersist.OPersist(fs_path)
        self.logger = logging.getLogger("OPersistPipeline")

    @classmethod
    def from_crawler(cls, crawler):
        #db_url = crawler.settings.get("DATABASE_URL", None)
        #return cls(db_url)
        return cls()

    def open_spider(self, spider):
        self.logger.debug("open_spider")
        self._op.open(allow_create=True)

    def close_spider(self, spider):
        self.logger.debug("close_spider")
        self._op.close()

    def process_item(self, item, spider):
        try:
            hashes, obj = opersist.utils.jsonChecksums(item["jsonld"])
            checksum_sha256 = hashes.get("sha256", None)
            if checksum_sha256 is None:
                raise scrapy.exception.DropItem(
                    f"No checksum for item: {item['url']}"
                )
            existing = self._op.getThingSha256(checksum_sha256)
            if existing is not None:
                raise scrapy.exception.DropItem(
                    f"Item already in store: {item['url']}"
                )

            identifier = item['identifier']
            if identifier is None:
                identifier = f"SHA256:{checksum_sha256}"
            format_id = item['format_id']
            series_id = item["series_id"] #Set in normalizepipeline
            alt_identifiers = item["alt_identifiers"]
            media_type = "application/ld+json"
            source = item['url']
            metadata = {
                "http_status": item["status"],
                "time_retrieved": opersist.utils.datetimeToJsonStr(item["time_retrieved"]),
            }
            obsoletes = None

            #TODO: Set these values from configuration for the data source
            submitter = None
            owner = None
            access_rules = None

            self.logger.info("Persisting %s", identifier)

            res = self._op.addThingBytes(
                obj,
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
                obsoletes=obsoletes
            )

        except Exception as e:
            self.logger.error(e)
        return item
