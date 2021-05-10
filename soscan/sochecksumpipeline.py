'''
Implements a pipeline that computes a reliable SHA256 checksum for an RDF graph.

The basic process is:

1. Load the graph into an RDF processor
2. Skolemize the graph to compute IDs for BNodes
3. Serialize the graph as sorted NTriples to a blob
4. Compute the checksum of the blob
'''
import logging
import hashlib
import scrapy.exceptions
import rdflib
import rdflib.compare


class SoChecksumPipeline:
    '''
    Computes a SHA256 checksum for an RDF graph.

    Expects item to have an entry "jsonld".

    If successful, the item is returned with the sha256 hex digest in item['checksum_sha256']
    '''
    def __init__(self):
        self.logger = logging.getLogger("SoChecksumPipeline")

    def process_item(self, item, spider):
        self.logger.debug("process_item: %s", item["url"])
        checksum = self.computeRDFChecksum(item["jsonld"], public_id=item["url"])
        if not checksum is None:
            item["checksum_sha256"] = checksum
            return item
        raise scrapy.exception.DropItem(
            f"Failed to compute checksum for document: {item['jsonld']}"
        )

    def computeRDFChecksum(self, jsonld, public_id):
        try:
            g = rdflib.ConjunctiveGraph()
            g.parse(data=jsonld, format="json-ld", publicID=public_id)
            gc = rdflib.compare.to_canonical_graph(g)
            rows = gc.serialize(format="nt11").decode().split("\n")
            sorted_rows = "\n".join(sorted(rows)).strip()
            hash = hashlib.sha256()
            hash.update(sorted_rows.encode("utf-8"))
            return hash.hexdigest()
        except Exception as e:
            self.logger.error("ComputeRDFChecksum failed: %s", e)
        return None

