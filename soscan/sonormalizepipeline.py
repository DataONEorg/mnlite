import logging
import scrapy.exceptions
import sonormal.normalize
import json
import opersist.rdfutils

class SoscanNormalizePipeline:
    """
    Normalization is needed for reliably computing checksums for the content.
    """

    def __init__(self):
        self.logger = logging.getLogger("SoscanNormalize")

    def process_item(self, item, spider):
        self.logger.debug("process_item: %s", item["url"])

        #TODO: load these from config
        force_lists = True
        require_identifier = True

        jsonld = item["jsonld"]
        if force_lists:
            jsonld = sonormal.normalize.forceSODatasetLists(jsonld)
        options = {
            "base":item["url"]
        }
        try:
            normalized = sonormal.normalize.normalizeJsonld(jsonld, options=options)
        except Exception as e:
            raise scrapy.exceptions.DropItem(f"JSON-LD normalization failed: {e}")
        ids = []
        try:
            _framed = sonormal.normalize.frameSODataset(normalized)
            ids = sonormal.normalize.getDatasetsIdentifiers(_framed)            
        except Exception as e:
            raise scrapy.exceptions.DropItem(f"JSON-LD identifier extract failed: {e}")
        if len(ids) < 1:
            raise scrapy.exceptions.DropItem(f"JSON-LD no ids, not a Dataset: {item['url']}")
        
        # TODO: identifiers
        # The process for handling of identifiers needs to be set in configuration

        # Use the first identifier value provided for series_id
        # PID will be computed from the object checksum
        item["alt_identifiers"] = None
        if len(ids) > 0:
            if len(ids[0]["identifier"]) > 0:
                item["series_id"] = ids[0]["identifier"][0]
                if len(ids[0]["identifier"]) > 1:
                    item["alt_identifiers"] = ids[0]["identifier"][1:]
            elif require_identifier:
                raise scrapy.exceptions.DropItem(f"JSON-LD no identifier: {item['url']}")
        item["identifier"] = None
        item["normalized"] = normalized
        item["format_id"] = opersist.rdfutils.DATASET_FORMATID
        # Obsoletes is not a property of the retrieved object but instead needs
        # to be inferred from the history associated with the object lineage
        # item["obsoletes"] = None
        return item
