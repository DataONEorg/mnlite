import logging
import scrapy.exceptions
import sonormal.normalize
import json
import opersist.rdfutils
from pathlib import Path

def consolidate_list(l: list, sep: str=', '):
    """
    Takes a list of strings and returns a list with one consolidated string,
    separated by ``sep``. This can help when a repository has mistakenly
    split their description/title strings.
    """
    consolidated = ''
    for li in l:
        if consolidated != '':
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

    def __init__(self, **kwargs):
        self.logger = logging.getLogger("SoscanNormalize")
        self.use_at_id = False
        if 'use_at_id' in kwargs:
            self.use_at_id = kwargs['use_at_id']
            self.logger.debug(f'Using @id as identifier: {self.use_at_id}')

    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        node_path = crawler.settings.get("STORE_PATH", None)
        mn_settings = Path(f'{node_path}/settings.json')
        if mn_settings.exists():
            with open(mn_settings) as cs:
                _cs: dict = json.loads(cs.read())
            for s in _cs:
                if s == 'use_at_id':
                    kwargs['use_at_id'] = _cs[s]
        return cls(**kwargs)


    def extract_identifier(self, ids, use_at_id):
        """
        Extract the series identifier from a list of identifiers structured like the following.

        [{'@id': ['https://doi.org/10.1234/5678'],
          'identifier': ['doi:10.1234/5678'],
          'url': ['https://doi.org/10.1234/5678']},
          ...]

        The first identifier is the one we should use as the series_id.
        """
        if len(ids) > 0:
            if len(ids[0]["identifier"]) > 0:
                return ids[0]["identifier"][0]
            else:
                # if the first identifier is an empty list, we need to look for others
                if use_at_id:
                    # if there is no identifier and use_at_id is True, use the @id value as the Dataset identifier
                    # This is a last resort measure and should be avoided if possible!
                    # it is needed for repositories that use GeoNetwork software which does not provide identifiers (as of Jan 2025)
                    for group in ids:
                        if len(group["@id"]) > 0:
                            self.logger.debug(f'Using @id {group["@id"][0]} for series_id')
                            return group["@id"][0]
                # if there is no identifier and use_at_id is False, use the first identifier value provided for series_id
                for group in ids:
                    if len(group["identifier"]) > 0:
                        self.logger.debug(f'Using identifier {group["identifier"][0]} for series_id')
                        return group["identifier"][0]              
        return None
    

    def extract_alt_identifiers(self, ids):
        """
        Extract the alternative identifiers from a list of identifiers structured like the following.

        [{'@id': ['https://doi.org/10.1234/5678'],
          'identifier': ['doi:10.1234/5678'],
          'url': ['https://doi.org/10.1234/5678']},
          ...]

        The first identifier is the one we should use as the series_id.
        Other identifiers are stored in a list of ``alt_identifiers``.
        """
        alt_ids = []
        # compile a list of alt_identifiers from all of the identifiers defined in the Dataset
        if len(ids) > 0:
            if len(ids[0]["identifier"]) > 0:
                alt_ids += ids[0]["identifier"][1:]
            alt_ids += ids[0]['url']
            alt_ids += ids[0]['@id']
            for group in ids[1:]:
                alt_ids += group["identifier"]
                alt_ids += group['url']
                alt_ids += group['@id']
        self.logger.debug(f'Extracted alt_identifiers: {alt_ids}')
        return list(set(alt_ids))


    def process_item(self, item, spider):
        self.logger.debug("process_item: %s", item["url"])

        # TODO: load these from config
        force_lists = True
        require_identifier = True

        jsonld: dict = item["jsonld"]
        version = jsonld.get('version', None)
        version = jsonld.get('@version', '1.1') if not version else version
        version = '1.0' if version == '1' else version
        jldversion = f'json-ld-{version}'
        self.logger.debug(f"process_item: version {jldversion}")
        options = {"base": item["url"], "processingMode": jldversion}

        if self.use_at_id:
            at_id = jsonld.get('@id', None)
            jsonld.update({'identifier': at_id})
            self.logger.debug(f'Using @id as identifier: {at_id}')

        # consolidate any lists that might cause the indexer to misfire
        name = jsonld.get('name', None)
        desc = jsonld.get('description', None)
        nstr, dstr = '[none]', '[none]'
        if name == None:
            graph = jsonld.get('@graph', None)
            if graph and isinstance(graph, list):
                name = graph[0].get('name', None)
                desc = graph[0].get('description', None)
                nstr = 'jsonld["@graph"][0]["name"]'
                dstr = 'jsonld["@graph"][0]["description"]'
            elif graph:
                # this probably doesn't exist..? try to get vars anyway
                self.logger.warn(f'Something weird has happened: the dataset graph at jsonld["@graph"] is not a list but instead {type(graph)}\nURL: {item["url"]}')
                self.logger.debug(f'Content of jsonld["@graph"]: {graph}')
                try:
                    name = graph.get('name', None)
                    desc = graph.get('description', None)
                except Exception as e:
                    raise scrapy.exceptions.DropItem(f"JSON-LD error ({repr(e)}): {e} - URL: {item['url']}")
                nstr = 'jsonld["@graph"]["name"]'
                dstr = 'jsonld["@graph"]["description"]'
        else:
            nstr = 'jsonld["name"]'
            dstr = 'jsonld["description"]'

        if name:
            if (isinstance(name, list)) and (len(name) > 1):
                self.logger.debug(f'Consolidating list of {len(name)} items at {nstr}: {name}')
                # can't think of a better way to do this
                exec(f'{nstr} = consolidate_list(name)')
                self.logger.debug(f'New list at {nstr}: {name}')
        else:
            raise scrapy.exceptions.DropItem(f"JSON-LD no dataset name found: {item['url']}")
        
        if desc:
            if (isinstance(desc, list)) and (len(desc) > 1):
                self.logger.debug(f'Consolidating list of {len(desc)} items at {dstr}: {desc}')
                exec(f'{dstr} = consolidate_list(desc)')
                self.logger.debug(f'New list at {dstr}: {desc}')
        else:
            self.logger.warning(f'JSON-LD no dataset description found: {item["url"]}')


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
                f"JSON-LD no ids: {item['url']}\n"
                f"Framed dataset:\n{_framed}"
            )

        # TODO: identifiers
        # The process for handling of identifiers needs to be set in configuration

        # Use the first identifier value provided for series_id
        # PID will be computed from the object checksum
        item["series_id"] = self.extract_identifier(ids, self.use_at_id)
        item["alt_identifiers"] = self.extract_alt_identifiers(ids)
        # if there are no identifiers, we need to drop the item
        if item["series_id"] is None:
            raise scrapy.exceptions.DropItem(
                f"JSON-LD no identifiers: {item['url']}"
            )
        if item["series_id"] == "doi:":
            raise scrapy.exceptions.DropItem(
                f"JSON-LD DOI URI empty: {item['url']}"
            )
        item["identifier"] = None
        item["normalized"] = normalized
        item["format_id"] = opersist.rdfutils.DATASET_FORMATID
        # Obsoletes is not a property of the retrieved object but instead needs
        # to be inferred from the history associated with the object lineage
        # item["obsoletes"] = None
        return item
