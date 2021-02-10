import logging
import scrapy.exceptions
import opersist.rdfutils
import json

class SoscanNormalizePipeline:
    """
    Normalization is useful for placing the JSON-LD in a more consistent structure
    that can simplify value extraction for processing operations such as indexing.
    """

    def __init__(self):
        self.logger = logging.getLogger("SoscanNormalize")

    def process_item(self, item, spider):
        self.logger.debug("process_item: %s", item["url"])

        try:
            res = opersist.rdfutils.normalizeSONamespace(item["jsonld"])
        except exception as e:
            raise scrapy.exceptions.DropItem(
                f"JSON-LD normalization failed 1: {e}"
            )
        context = {
            "@context": {
                "@vocab": "http://schema.org/"
            }
        }
        force_lists = [
            "http://schema.org/identifier",
            "http://schema.org/creator",
        ]
        try:
            normalized = opersist.rdfutils.normalizeJSONLDStructure(
                res,
                base=item["url"],
                context=context,
                force_lists=force_lists,
            )
        except exception as e:
            raise scrapy.exceptions.DropItem(
                f"JSON-LD normalization failed 2: {e}"
            )
        try:
            ids = opersist.rdfutils.extractIdentifiers(normalized)
        except exception as e:
            raise scrapy.exceptions.DropItem(
                f"JSON-LD normalization failed 3: {e}"
            )

        #TODO: identifiers
        # The process for handling of identifiers needs to be set in configuration

        # Use the first identifier value provided for series_id
        # PID will be computed from the object checksum

        print("NORMALIZED =============")
        #print(json.dumps(normalized, indent=2))
        print(json.dumps(ids, indent=2))
        print("NORMALIZED =============")

        item["alt_identifiers"] = None
        if len(ids) > 0:
            item["series_id"] = ids[0]["identifier"][0]
            if len(ids[0]["identifier"])> 1:
                item["alt_identifiers"] = ids[0]["identifier"][1:]
        item["identifier"] = None
        item["jsonld"] = normalized
        item["format_id"] = opersist.rdfutils.DATASET_FORMATID
        # Obsoletes is not a property of the retrieved object but instead needs
        # to be inferred from the history associated with the object lineage
        #item["obsoletes"] = None
        return item

