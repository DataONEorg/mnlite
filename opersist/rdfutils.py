"""
Miscellaneous utilities for working with RDF / JSON-LD
"""

import logging
import io
import copy
import hashlib
import json
import pyld

HASH_BLOCK_SIZE = 8192
SO_HTTP = "http://schema.org/"
SO_HTTPS = "https://schema.org/"
SO_FIX = SO_HTTPS
SO_NS = SO_HTTP
SO_CONTEXT = {
    "@context": {
        "@vocab": SO_NS,
    }
}
DEFAULT_BASE = "https://example.net/data/"
EXAMPLE_CONTEXT_URL = "http://example.net/context"

# Setup the context cache to return a valid jsonld document when requesting
# the example json-ld context
CONTEXT_CACHE = {
    EXAMPLE_CONTEXT_URL: {
        "contentType": "application/ld+json",
        "contextUrl": None,
        "documentUrl": EXAMPLE_CONTEXT_URL,
        "document": "{}",
    }
}

DATASET_FORMATID = "science-on-schema.org/Dataset/1.2;ld+json"


def cachingDocumentLoader(url, options={}):
    L = logging.getLogger("documentLoader")
    L.info("DOC LOADER URL = %s", url)
    if url in CONTEXT_CACHE:
        return CONTEXT_CACHE[url]
    loader = pyld.jsonld.requests_document_loader()
    resp = loader(url, options=options)
    CONTEXT_CACHE[url] = resp
    return resp


pyld.jsonld.set_document_loader(cachingDocumentLoader)


def normalizeJSONLDStructure(doc, base=None, context=None, force_lists=None):
    """
    Return the json-ld document after expanding and flattening.

    This resolves many discrepancies in serialization and is
    necessary before computing checksums for future comparison.

    Args:
        doc: The json-ld structure
        base: Base URL to be used for expansion
        context: Context to use when flattening, defaults to {}
        force_lists: Force new context

    Returns:
        json-ld document after processing
    """
    L = logging.getLogger("normalizeJSONLDStructure")
    if force_lists is None:
        force_lists = []
    options = {"graph": True, "compactArrays": True, "ordered": True}
    if context is None:
        context = {"@context": {}}
    expanded = pyld.jsonld.expand(doc, {"base": base})
    for term in force_lists:
        new_v = {"@container": "@list"}
        v = context["@context"].get(term, None)
        if isinstance(v, str):
            context["@context"][term] = [v, new_v]
        elif isinstance(v, list):
            context["@context"][term].append(new_v)
        elif isinstance(v, dict):
            context["@context"][term].update(new_v)
        else:
            context["@context"][term] = new_v
    # L.info("CONTEXT: %s", context)
    # L.info("EXPANDED: %s", expanded)
    #flat = pyld.jsonld.flatten(expanded, context, options)
    flat = pyld.jsonld.compact(expanded, context, options)
    return flat


def adjustSOContext(ctx):
    """
    Adjust context of a JSON-LD document that references the schema.org context.

    As of this writing, schema.org uses the namespace "http://schema.org/" in its context:

        https://schema.org/docs/jsonldcontext.jsonld

    Args:
        ctx: A JSON-LD context.

    Returns:
        context adjusted for the schema.org namespace SO_NS
    """

    def _adjustSONS(v):
        if isinstance(v, dict):
            return adjustSOContext(v)
        if v.startswith(SO_FIX):
            return SO_NS + v[len(SO_FIX) :]
        return v

    # Only adjust the namespaces, not pointers to locations of contexts.
    if isinstance(ctx, dict):
        uctx = {}
        for k, v in ctx.items():
            if k == "@vocab":
                uctx[k] = _adjustSONS(v)
            elif not k.startswith("@"):
                nk = _adjustSONS(k)
                uctx[nk] = _adjustSONS(v)
            else:
                uctx[k] = v
        return uctx
    elif isinstance(ctx, str):
        if ctx == "http://schema.org":
            # The URL http://schema.org fails under context negotiation
            ctx = "http://schema.org/"
    return ctx


def normalizeSONamespace(source):
    '''
    Adjusts common errors in schema.org namespace.

    This is a bit of a hack to try and force content to use the
    authoritative schema.org namespace of "http://schema.org/".
    It should work for most common cases encountered in the wild.

    There is some controversy over this, with some claiming "https",
    however as of this writing, the context document can be retrieved
    from:

      https://schema.org/docs/jsonldcontext.jsonld

    That document specifies "http://schema.org/" as the namespace.

    Args:
        source: JSON-LD

    Returns: JSON-LD structure with possibly adjusted SO namespace

    '''
    if not isinstance(source, list):
        source = [
            source,
        ]
    for i in range(0, len(source)):
        doc = source[i]
        res = adjustSOContext(doc.get("@context", {}))
        source[i]["@context"] = res
    return source


def extractIdentifiers(jsonld: dict):
    """
    Extract PID, series_id, alt_identifiers from a block of JSON-LD

    Args:
        jsonld: normalized JSON ld document

    Returns:
        dict with pid, sid, and alternates

    """

    def _identifierValue(ident):
        if isinstance(ident, str):
            return ident
        if isinstance(ident, dict):
            v = ident.get("value", None)
            if v is None:
                v = ident.get("url", None)
            return v
        return str(ident)

    def _identifierValues(ident_list):
        res = []
        if ident_list is None:
            return res
        if isinstance(ident_list, str):
            return [_identifierValue(ident_list)]
        if isinstance(ident_list, dict):
            return [_identifierValue(ident_list)]
        for ident in ident_list:
            v = _identifierValue(ident)
            if not v is None:
                res.append(v)
        return res

    ids = []
    id_template = {
        "@id": None,  # Dataset.@id
        "url": None,  # Dataset.url
        "identifier": [],  # Values of any identifiers
    }
    for g in jsonld.get("@graph", []):
        g_type = g.get("@type", "")
        if g_type == SO_NS + "Dataset" or g_type == "Dataset":
            dsid = id_template.copy()
            dsid["@id"] = g.get("@id", None)
            dsid["url"] = g.get("url", None)
            identifiers = g.get(SO_NS + "identifier", None)
            if identifiers is None:
                identifiers = g.get("identifier", None)
            dsid["identifier"] = _identifierValues(identifiers)
            ids.append(dsid)
    return ids


def XXcomputeJSONLDChecksums(jsonld: dict):
    jn = pyld.jsonld.normalize(jsonld, {"algorithm": "URDNA2015"})
    # , "format": "jsonld"
    # encjn = jn.encode("utf-8")
    encjn = json.dumps(jn, indent=2).encode("utf-8")
    hashes = {
        "sha256": hashlib.sha256(encjn).hexdigest(),
        "sha1": hashlib.sha1(encjn).hexdigest(),
        "md5": hashlib.md5(encjn).hexdigest(),
    }
    return hashes, jn


def XXcomputeJSONLDChecksumsNQ(jsonld: dict):
    jn = pyld.jsonld.normalize(
        jsonld, {"algorithm": "URDNA2015", "format": "application/n-quads"}
    )
    encjn = jn.encode("utf-8")
    hashes = {
        "sha256": hashlib.sha256(encjn).hexdigest(),
        "sha1": hashlib.sha1(encjn).hexdigest(),
        "md5": hashlib.md5(encjn).hexdigest(),
    }
    return hashes


def XXnormalizeStructure(source, base=None, context=None, force_lists=[]):
    """
    Adjust the structure of a JSON-LD graph for some level of consistency.

    The process involves expansion, then compaction with a schema.org centric
    context. schema.org names appearing in force_lists will have the @container
    set to @lsit to ensure order is preserved.

    The resulting JSON-LD has:

      1. "@graph" is used regardless of how many graphs are present in the dataset
      2. Arrays are compacted
      3. The @context may be adjusted to specify @vocab of SO_NS

    Args:
        source: the souce JSON-LD graph
        context: The context to use for the newly compacted document
        base: Optional document base (i.e. url from which it was downloaded) to resolve relative URIs
        force_lists: list of elements to be set as ordered lists

    Returns:
        normalized JSON-LD structure
    """
    # Adjust namespace to match that of the remote schema.org namespace
    L = logging.getLogger("normalizeStructure")
    doc = normalizeSONamespace(source)
    if context is None:
        context = copy.deepcopy(SO_CONTEXT)
    try:
        # expand the json-ld to remove namespace abbreviations
        options = {}
        if base is not None:
            options["base"] = base
        expanded = pyld.jsonld.expand(doc, options)
        # Compact the expanded graph with the original context that has modified namespace
        # L.debug("EXPANDED: %s", json.dumps(expanded, indent=2))
        options = {
            "graph": True,
            "compactArrays": True,
        }
        normalized = pyld.jsonld.compact(expanded, context, options)
        # L.debug("NORMALIZED: %s", json.dumps(normalized, indent=2))
        # normalized["@context"]["@vocab"] = SO_HTTPS
        for fl in force_lists:
            item = normalized["@context"].get(fl, {})
            item["@container"] = "@list"
            normalized["@context"][fl] = item
        # Re-compact after manually adjusting the containers
        ctx = normalized["@context"]
        # L.debug("CTX: %s", ctx)
        return pyld.jsonld.compact(normalized, ctx, options)
    except Exception as e:
        L.error("Normalize failed: %s", e)
        # L.error("Cache: %s", CONTEXT_CACHE)
    return None
