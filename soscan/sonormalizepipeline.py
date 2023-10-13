import logging
import scrapy.exceptions
import sonormal.normalize
import json
import opersist.rdfutils


class SoscanNormalizePipeline:
    """
    Normalization is needed for reliably computing checksums for the content.

    This is the rabbit hole.

    The PID is from the SHA256 checksum.
    The checksum must be reliably computable.
    The SID is from an identifier, if provided.
    If there's more than one identifier, we take the first one.
    The first one may not be the same as before, unless it's an ordered list...

    So, Alice does this:
    1. Keep the original JSONLD - preserved for later distribution
    2. Create a copy of the JSONLD normalized to http://schema.org/ and expanded
    3. Frame the normalized JSONLD with a Dataset structure
    4. Get the identifier from the framed JSONLD
    """

    def __init__(self):
        self.logger = logging.getLogger("SoscanNormalize")

    def process_item(self, item, spider):
        self.logger.debug("process_item: %s", item["url"])

        # TODO: load these from config
        force_lists = True
        require_identifier = True

        jsonld = item["jsonld"]
        version = jsonld.get('version', None)
        version = jsonld.get('@version', '1.1') if not version else version
        version = '1.0' if version == '1' else version
        jldversion = f'json-ld-{version}'
        self.logger.debug(f"process_item: version {jldversion}")
        options = {"base": item["url"], "processingMode": jldversion}
        try:
            normalized = sonormal.sosoNormalize(jsonld, options=options)
        except Exception as e:
            raise scrapy.exceptions.DropItem(f"JSON-LD normalization failed: {e}")

        ids = []
        try:
            _framed = sonormal.normalize.frameSODataset(normalized, options=options)
            ids = sonormal.normalize.getDatasetsIdentifiers(_framed)
        except Exception as e:
            raise scrapy.exceptions.DropItem(f"JSON-LD identifier extract failed: {e}")
        if len(ids) < 1:
            raise scrapy.exceptions.DropItem(
                f"JSON-LD no ids, not a Dataset: {item['url']}"
            )

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
                raise scrapy.exceptions.DropItem(
                    f"JSON-LD no identifier: {item['url']}"
                )
        item["identifier"] = None
        item["normalized"] = normalized
        item["format_id"] = opersist.rdfutils.DATASET_FORMATID
        # Obsoletes is not a property of the retrieved object but instead needs
        # to be inferred from the history associated with the object lineage
        # item["obsoletes"] = None
        return item
