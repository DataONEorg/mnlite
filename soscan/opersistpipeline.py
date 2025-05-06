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
import json
from pathlib import Path
import logging
import opersist
import opersist.utils
import sonormal.checksums
import scrapy.exceptions


class OPersistPipeline:
    def __init__(self, fs_path, **kwargs):
        self._op = opersist.OPersist(fs_path)
        self.logger = logging.getLogger("OPersistPipeline")
        self.dedup_nodes = []
        if kwargs.get("dedup_nodes", False):
            self.logger.debug(f"Deduplication nodes: {kwargs['dedup_nodes']}")
            dedup_nodes = 0
            for n in kwargs["dedup_nodes"]:
                self.dedup_nodes.append(opersist.OPersist(n))
                dedup_nodes += 1
            self.logger.info(f"Added {dedup_nodes} deduplication node(s)")

    @classmethod
    def from_crawler(cls, crawler, **kwargs):
        # db_url = crawler.settings.get("DATABASE_URL", None)
        # return cls(db_url)
        fs_path = crawler.settings.get("STORE_PATH", None)
        if fs_path is None:
            raise Exception("STORE_PATH configuration is required!")
        if not os.path.exists(fs_path):
            raise ValueError(f"STORE_PATH {fs_path} not found.")
        mn_settings = Path(f'{fs_path}/settings.json')
        # add deduplication nodes
        kwargs["dedup_nodes"] = []
        if mn_settings.exists():
            with open(mn_settings) as cs:
                _cs: dict = json.loads(cs.read())
            for s in _cs:
                if s == "dedup_nodes":
                    if isinstance(_cs[s], list):
                        for n in _cs[s]:
                            if Path(n).exists():
                                kwargs["dedup_nodes"].append(n)
                            else:
                                raise ValueError(f"Deduplication node directory {n} not found.")
                    else:
                        if Path(_cs[s]).exists():
                            kwargs["dedup_nodes"].append(_cs[s])
                        else:
                            raise ValueError(f"Deduplication node directory {_cs[s]} not found.")
        return cls(fs_path, **kwargs)

    def open_spider(self, spider):
        self.logger.debug("open_spider")
        self._op.open(allow_create=True)
        self.logger.debug(f"OPersist {self._op} opened")
        for dedup_node in self.dedup_nodes:
            dedup_node.open(allow_create=False)
            dedup_node_name = Path(dedup_node.fs_path).name
            self.logger.debug(f"Deduplication node {dedup_node_name} opened")

    def close_spider(self, spider):
        self.logger.debug("close_spider")
        self._op.close()
        self.logger.debug("OPersist connection closed")
        for dedup_node in self.dedup_nodes:
            dedup_node.close()
            dedup_node_name = Path(dedup_node.fs_path).name
            self.logger.debug(f"Deduplication node {dedup_node_name} closed")

    def process_item(self, item, spider):
        try:
            #hashes, _canonical = sonormal.checksums.jsonChecksums(item["normalized"])
            hashes, _canonical = sonormal.checksums.jsonChecksums(item["jsonld"], canonicalize=False)
            checksum_sha256 = hashes.get("sha256", None)
            if checksum_sha256 is None:
                raise scrapy.exceptions.DropItem(f"No checksum for item: {item['url']}")
            existing = self._op.getThingSha256(checksum_sha256)
            if existing is not None:
                self.logger.debug(
                    f"Found existing entry:\n{item['url']}\n{checksum_sha256}\n{existing.series_id}\n{existing.file_name}\n==="
                )
                raise scrapy.exceptions.DropItem(
                    f"Item already in store: {item['url']} sha256:{checksum_sha256}"
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

            # Check for duplicates in deduplication nodes
            for dedup_node in self.dedup_nodes:
                existing = dedup_node.getThingsSIDOrAltIdentifier(identifier)
                if existing is not None:
                    dedup_node_name = Path(dedup_node.fs_path).name
                    self.logger.debug(
                        f"Found existing entry in dedup node {dedup_node_name}:\n{item['url']}\n{checksum_sha256}\n{existing.series_id}\n{existing.file_name}\n==="
                    )
                    raise scrapy.exceptions.DropItem(
                        f"Item already in dedup node {dedup_node_name}: {item['url']} sha256:{checksum_sha256}"
                    )

            # TODO: Set these values from configuration for the data source
            submitter = None
            owner = None
            access_rules = None

            self.logger.debug("Persisting %s", identifier)

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
            return
        return item
