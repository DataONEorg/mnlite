import logging
import scrapy.exceptions
import sonormal.normalize
import json
import opersist.rdfutils

def consolidate_list(l: list, sep: str=', '):
    """
    Takes a list of strings and returns a list with one consolidated string,
    separated by ``sep``. This can help when a repository has mistakenly
    split their description/title strings.
    """
    consolidated = ''
    for li in l:
        consolidated += sep
        consolidated += li
    return [consolidated]


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

        # consolidate any lists that might cause the indexer to misfire
        if (isinstance(normalized["@graph"][0]["name"], list)) and (len(normalized["@graph"][0]["name"]) > 1):
            l = normalized["@graph"][0]["name"]
            self.logger.debug(f'Consolidating list of {len(l)} items at ["@graph"][0]["name"]: {l}')
            normalized["@graph"][0]["name"] = consolidate_list(normalized["@graph"][0]["name"])
            self.logger.debug(f'New list at ["@graph"][0]["name"]: {normalized["@graph"][0]["name"]}')

        if (isinstance(normalized["@graph"][0]["description"], list)) and (len(normalized["@graph"][0]["description"]) > 1):
            l = normalized["@graph"][0]["description"]
            self.logger.debug(f'Consolidating list of {len(l)} items at ["@graph"][0]["description"]: {l}')
            normalized["@graph"][0]["description"] = consolidate_list(normalized["@graph"][0]["description"])
            self.logger.debug(f'New list at ["@graph"][0]["description"]: {normalized["@graph"][0]["description"]}')

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
        item["series_id"] = None
        item["alt_identifiers"] = []
        if len(ids) > 0:
            self.logger.debug(f"ids found: {ids}")
            if len(ids[0]["identifier"]) > 0:
                item["series_id"] = ids[0]["identifier"][0]
                self.logger.debug(f'Using first identifier for series_id: {item["series_id"]}')
                if len(ids[0]["identifier"]) > 1:
                    item["alt_identifiers"] = ids[0]["identifier"][1:]
                    self.logger.debug(f'alt_identifiers: {item["alt_identifiers"]}')
            else:
                # if the first identifier is an empty list, we need to look for others
                self.logger.warning(f'Empty identifier in first Dataset grouping')
                g = 0
                for group in ids:
                    g += 1
                    self.logger.info(f'Dataset grouping {g}: {group}')
                    if len(group["identifier"]) > 0:
                        if item["series_id"] is None:
                            item["series_id"] = group["identifier"][0]
                            self.logger.info(f'Using identifier {g} for series_id: {item["series_id"]}')
                            if len(group["identifier"]) > 1:
                                item["alt_identifiers"].append(group["identifier"][1:])
                        else:
                            item["alt_identifiers"].append(group["identifier"][0:])
                self.logger.debug(f'alt_identifiers: {item["alt_identifiers"]}')
        if require_identifier and item["series_id"] is None:
            raise scrapy.exceptions.DropItem(
                f"JSON-LD no identifier: {item['url']}"
            )
        if item["series_id"] == "doi:":
            raise scrapy.exceptions.DropItem(
                f"JSON-LD identifier empty: {item['url']}"
            )
        item["identifier"] = None
        item["normalized"] = normalized
        item["format_id"] = opersist.rdfutils.DATASET_FORMATID
        # Obsoletes is not a property of the retrieved object but instead needs
        # to be inferred from the history associated with the object lineage
        # item["obsoletes"] = None
        return item
