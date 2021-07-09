"""
Miscellaneous utilities for working with RDF / JSON-LD
"""

import logging
import io
import copy

try:
    import orjson as json
except ModuleNotFoundError:
    import json

import pyld
import re


SO_HTTP = "http://schema.org/"
SO_HTTPS = "https://schema.org/"
SO_FIX = SO_HTTPS
SO_NS = SO_HTTPS
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

# DataONE formatId for the Dataset structure
DATASET_FORMATID = "science-on-schema.org/Dataset/1.2;ld+json"

# regexp to match the typical location of the schema.org remote context
SO_MATCH = re.compile("http(s)?\://schema.org(/)?")

SO_ = "https://schema.org/"
SO_DATASET = f"{SO_}Dataset"
SO_IDENTIFIER = f"{SO_}identifier"
SO_VALUE = f"{SO_}value"
SO_URL = f"{SO_}url"

# Location of the schema.org context document
SO_CONTEXT_LOCATION = "https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/releases/12.0/schemaorgcontext.jsonld"

# Frame used to force the structure of a schema.org/Dataset for
# value extraction.
DATASET_FRAME = {
    "@context": {"@vocab": "https://schema.org/"},
    "@type": "Dataset",
    "identifier": {},
    "creator": {},
}


def cachingDocumentLoader(url, options={}):
    L = logging.getLogger("documentLoader")
    L.debug("DOC LOADER URL = %s", url)
    if SO_MATCH.match(url) is not None:
        L.info("Forcing schema.org v12 context")
        url = SO_CONTEXT_LOCATION
    if url in CONTEXT_CACHE:
        return CONTEXT_CACHE[url]
    loader = pyld.jsonld.requests_document_loader()
    resp = loader(url, options=options)
    CONTEXT_CACHE[url] = resp
    return resp


# inject the custom document loader into pyld
#pyld.jsonld.set_document_loader(cachingDocumentLoader)


def XXextractDatasetIdentifiers(jsonld: dict):
    """
    Extract PID, series_id, alt_identifiers from a block of JSON-LD.

    The JSON-LD is expected to be framed with the DATASET_FRAME
    prior to calling this method.

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


def _getIdentifiers(doc):
    ids = []
    v = doc.get("@value", None)
    if not v is None:
        ids.append(v)
        return ids
    vs = doc.get(SO_VALUE, [])
    for av in vs:
        v = av.get("@value", None)
        if v is not None:
            ids.append(v)
    return ids


def _getListIdentifiers(doc):
    ids = []
    for ident in doc.get("@list", []):
        ids += _getIdentifiers(ident)
    return ids


def _getDatasetIdentifiers(jdoc):
    ids = {"@id": [], "url": [], "identifier": []}
    t = jdoc.get("@type", [])
    if SO_DATASET in t:
        _id = jdoc.get("@id", None)
        if _id is not None:
            ids["@id"].append(_id)
        _urls = jdoc.get(SO_URL, [])
        for _url in _urls:
            u = _url.get("@id", None)
            if not u is None:
                ids["url"].append(u)
        for ident in jdoc.get(SO_IDENTIFIER, []):
            ids["identifier"] += _getListIdentifiers(ident)
            ids["identifier"] += _getIdentifiers(ident)
    return ids


def getDatasetsIdentifiers(jdoc):
    ids = []
    for doc in jdoc:
        ids.append(_getDatasetIdentifiers(doc))
    return ids


def normalizeJsonLd(doc, base=None):
    opts = {}
    if not base is None:
        opts["base"] = base
    ndoc = pyld.jsonld.expand(doc, options=opts)
    return ndoc


def frameJsondldDataset(doc, base=None):
    opts = {}
    if not base is None:
        opts["base"] = base
    fdoc = pyld.jsonld.frame(doc, DATASET_FRAME, options=opts)
    return fdoc


def normalizeJsonld(doc, options={}):
    """
    Normalize the structure of the provided json-ld document.

    The document is converted to rdf and back again, then expanded
    to remove an
    """
    opts = {"base": DEFAULT_BASE}
    opts.update(options)
    rdoc = pyld.jsonld.to_rdf(doc, options=opts)
    ndoc = pyld.jsonld.from_rdf(rdoc)
    return pyld.jsonld.expand(ndoc)


## The following to be discarded.


def XXadjustSOContext(ctx):
    """
    Adjust context of a JSON-LD document that references the schema.org context.

    The soon to be released version 12 of schema.org uses a namespace of "https://schema.org/"
    with the context document:

        https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/releases/12.0/schemaorgcontext.jsonld

    Args:
        ctx: A JSON-LD context, i.e. the value of "@context"

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
            ctx = "https://schema.org/"
    return ctx


def XXnormalizeSONamespace(source):
    """
    Adjusts common errors in schema.org namespace.

    This is a bit of a hack to try and force content to use the
    schema.org namespace of "https://schema.org/". It should work for most common
    cases encountered in the wild.

    There is some controversy over this, with some claiming "http",
    however as of version 12 of schema.org the context will be:

      #https://schema.org/docs/jsonldcontext.jsonld
      https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/releases/12.0/schemaorgcontext.jsonld


    That document specifies "https://schema.org/" as the namespace.

    Args:
        source: JSON-LD

    Returns: JSON-LD structure with possibly adjusted SO namespace

    """
    if not isinstance(source, list):
        source = [
            source,
        ]
    for i in range(0, len(source)):
        doc = source[i]
        res = adjustSOContext(doc.get("@context", {}))
        source[i]["@context"] = res
    return source


def XXnormalizeJSONLDStructure(doc, base=None, context=None, force_lists=None):
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
    # flat = pyld.jsonld.flatten(expanded, context, options)
    flat = pyld.jsonld.compact(expanded, context, options)
    return flat
