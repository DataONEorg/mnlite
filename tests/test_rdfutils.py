import os
import logging
import tempfile
import json
import pyld.jsonld
import pytest
import opersist.utils
import opersist.rdfutils

test_ctx = [
    ["https://schema.org/", "https://schema.org/"],
    ["http://schema.org/", "http://schema.org/"],
    [
        ["https://schema.org/", "https://example.net/"],
        ["https://schema.org/", "https://example.net/"],
    ],
    [
        {"@vocab": "https://schema.org/"},
        {"@vocab": "http://schema.org/"},
    ],
    [
        {"SO": "https://schema.org/", "@vocab": "https://example.net/"},
        {"SO": "http://schema.org/", "@vocab": "https://example.net/"},
    ],
    [
        {
            "@vocab": "https://schema.org/",
            "https://schema.org/name": {"@container": "@list"},
        },
        {
            "@vocab": "http://schema.org/",
            "http://schema.org/name": {"@container": "@list"},
        },
    ],
    [
        {
            "@vocab": "https://schema.org/",
            "name": {"@container": "@list"},
        },
        {
            "@vocab": "http://schema.org/",
            "name": {"@container": "@list"},
        },
    ],
]


@pytest.mark.parametrize("ctx, expected", test_ctx)
def test_adjustContext(ctx, expected):
    L = logging.getLogger("test_adjustContext")
    result = opersist.rdfutils.adjustSOContext(ctx)
    L.info(json.dumps(result, indent=2))
    assert result == expected


test_docs = [
    [
        {"@context": "http://schema.org/", "@id": "test_1", "@type": "Thing"},
        [{"@context": "http://schema.org/", "@id": "test_1", "@type": "Thing"}],
        {
            "types": [
                "http://schema.org/Thing",
            ]
        },
    ],
    [
        {
            "@context": [opersist.rdfutils.EXAMPLE_CONTEXT_URL, "http://schema.org/"],
            "@id": "test_1a",
            "@type": "Thing",
        },
        [
            {
                "@context": [opersist.rdfutils.EXAMPLE_CONTEXT_URL, "http://schema.org/"],
                "@id": "test_1a",
                "@type": "Thing",
            }
        ],
        {
            "types": [
                "http://schema.org/Thing",
            ]
        },
    ],
    [
        {
            "@context": {"@vocab": "http://schema.org/"},
            "@id": "test_2",
            "@type": "Thing",
        },
        [
            {
                "@context": {"@vocab": "http://schema.org/"},
                "@id": "test_2",
                "@type": "Thing",
            }
        ],
        {
            "types": [
                "http://schema.org/Thing",
            ]
        },
    ],
    [
        {
            "@context": {"@vocab": "https://schema.org/"},
            "@id": "test_3",
            "@type": "Thing",
        },
        [
            {
                "@context": {"@vocab": "http://schema.org/"},
                "@id": "test_3",
                "@type": "Thing",
            }
        ],
        {
            "types": [
                "http://schema.org/Thing",
            ]
        },
    ],
    [
        [
            {"@context": "http://schema.org/", "@id": "test_4a", "@type": "Thing"},
            {"@context": "https://schema.org/", "@id": "test_4b", "@type": "Thing"},
        ],
        [
            {"@context": "http://schema.org/", "@id": "test_4a", "@type": "Thing"},
            {"@context": "https://schema.org/", "@id": "test_4b", "@type": "Thing"},
        ],
        {
            "types": [
                "http://schema.org/Thing",
                "http://schema.org/Thing",
            ]
        },
    ],
    [
        [
            {"@context": "https://schema.org/", "@id": "test_5a", "@type": "Thing"},
            {
                "@context": {"@vocab": "https://schema.org/"},
                "@id": "test_5b",
                "@type": "Thing",
            },
        ],
        [
            {"@context": "https://schema.org/", "@id": "test_5a", "@type": "Thing"},
            {
                "@context": {"@vocab": "http://schema.org/"},
                "@id": "test_5b",
                "@type": "Thing",
            },
        ],
        {
            "types": [
                "http://schema.org/Thing",
                "http://schema.org/Thing",
            ]
        },
    ],
    [
        [
            {
                "@context": {"@vocab": "https://schema.org/"},
                "@id": "test_6a",
                "@type": "Thing",
                "author": ["Joe", "Fred", "Jane"],
            },
            {
                "@context": {"@vocab": "https://schema.org/"},
                "@id": "test_6b",
                "@type": "Thing",
            },
        ],
        [
            {
                "@context": {"@vocab": "http://schema.org/"},
                "@id": "test_6a",
                "@type": "Thing",
                "author": ["Joe", "Fred", "Jane"],
            },
            {
                "@context": {"@vocab": "http://schema.org/"},
                "@id": "test_6b",
                "@type": "Thing",
            },
        ],
        {
            "types": [
                "http://schema.org/Thing",
                "http://schema.org/Thing",
            ]
        },
    ],
]


@pytest.mark.parametrize("doc, expected, ignore", test_docs)
def test_normalizeSONamespace(doc, expected, ignore):
    L = logging.getLogger('test_normalizeSONamespace')
    res = opersist.rdfutils.normalizeSONamespace(doc)
    L.info(json.dumps(res,indent=2))
    assert res == expected


@pytest.mark.parametrize("doc, ignore, expected", test_docs)
def test_normalizeStructure(doc, ignore, expected):
    L = logging.getLogger('test_normalizeStructure')
    L.info("DOC = %s", json.dumps(doc, indent=2))
    ndoc = opersist.rdfutils.normalizeSONamespace(doc)
    res = opersist.rdfutils.normalizeJSONLDStructure(ndoc)
    types = []
    for g in res.get("@graph", []):
        for k,v in g.items():
            if k == "@type":
                types.append(v)
    L.info("RES = %s", json.dumps(res, indent=2))
    assert len(types) == len(expected['types'])
    for t in types:
        assert t in expected['types']


def test_ns_normalize_multi():
    L = logging.getLogger('test_ns_normalize_multi')
    doc = {
        "@context": {"@vocab": "https://example.net", "SO": "http://schema.org/"},
        "@id": "multi_1",
        "@type": "Thing",
    }
    res = opersist.rdfutils.normalizeSONamespace(doc)
    L.info(json.dumps(res, indent=2))
    ns = res[0].get("@context", {}).get("SO", "")
    assert ns == "http://schema.org/"


def test_ns_normalize_multi_2():
    # Should not change a list of referenced contexts since it is not possible
    # to know what the contexts are referring to without resolving them.
    L = logging.getLogger('test_ns_normalize_multi_2')
    doc = {
        "@context": [
            opersist.rdfutils.EXAMPLE_CONTEXT_URL,
            "https://schema.org/",
        ],
        "@id": "multi_2",
        "@type": "Thing",
    }
    res = opersist.rdfutils.normalizeSONamespace(doc)
    L.info(json.dumps(res, indent=2))
    expected = [opersist.rdfutils.EXAMPLE_CONTEXT_URL,"https://schema.org/"]
    ns = res[0].get("@context", [])
    assert ns == expected


test_identifiers = [
    [
        {
            "@context": "https://schema.org/",
            "@id": "test_1",
            "@type": "Dataset",
            "identifier": "test_1",
        },
        [
            "test_1",
        ],
    ],
    [
        {
            "@context": {"@vocab": "https://schema.org/"},
            "@id": "test_2",
            "@type": "Dataset",
            "identifier": ["test_1", "test_2"],
        },
        ["test_1", "test_2"],
    ],
    [
        {
            "@context": {"@vocab": "https://schema.org/"},
            "@id": "test_3",
            "@type": "Dataset",
            "identifier": {"@list": ["test_1", "test_2"]},
        },
        ["test_1", "test_2"],
    ],
    [
        {
            "@context": {
                "@vocab": "https://schema.org/",
                "identifier": {"@container": "@list"},
            },
            "@id": "test_4",
            "@type": "Dataset",
            "identifier": ["test_1", "test_2"],
        },
        ["test_1", "test_2"],
    ],
]


@pytest.mark.parametrize("doc,expected", test_identifiers)
def test_identifiers(doc, expected):
    L = logging.getLogger("test_identifiers")
    res = opersist.rdfutils.normalizeSONamespace(doc)
    res = opersist.rdfutils.normalizeJSONLDStructure(
        res,
        base="https://example.net/test/",
        context=None,
        force_lists=[
            "http://schema.org/identifier"
        ],
    )
    ids = opersist.rdfutils.extractIdentifiers(res)
    L.info("CTX-normal: %s", json.dumps(res, indent=2))
    L.info("IDs: %s", ids)
    assert len(expected) == len(ids[0]["identifier"])
    for ex in expected:
        assert ex in ids[0]["identifier"]


test_hashes = [
    [
        {
            "@context": {
                "@vocab": "https://schema.org/",
                "identifier": {"@container": "@list"},
            },
            "@id": "test_1",
            "@type": "Dataset",
            "identifier": ["test_1", "test_2"],
        },
        {
            "sha256": "096b1811d6c6160c2ef4ea6ed5a5f48befb915e0460a3be06c4e9904467d42a0",
            "sha1": "b70ff4099c73bf4845ab8e1c2ab0372707250b48",
            "md5": "c35ba0b78643119ea4dfff1c24d495c3"
        }
    ],
    [
        {
            "@context": [
                "https://schema.org/",
                {"identifier":{"@container":"@list"}}
            ],
            "@id": "test_1",
            "@type": "Dataset",
            "identifier": ["test_1", "test_2"],
        },
        {
            "sha256": "096b1811d6c6160c2ef4ea6ed5a5f48befb915e0460a3be06c4e9904467d42a0",
            "sha1": "b70ff4099c73bf4845ab8e1c2ab0372707250b48",
            "md5": "c35ba0b78643119ea4dfff1c24d495c3"
        }
    ],
    [
        {
            "@context": [
                "http://schema.org/",
                {"identifier": {"@container": "@list"}}
            ],
            "identifier": ["test_1", "test_2"],
            "@id": "test_1",
            "@type": "Dataset",
        },
        {
            "sha256": "096b1811d6c6160c2ef4ea6ed5a5f48befb915e0460a3be06c4e9904467d42a0",
            "sha1": "b70ff4099c73bf4845ab8e1c2ab0372707250b48",
            "md5": "c35ba0b78643119ea4dfff1c24d495c3"
        }
    ]
]

@pytest.mark.parametrize("doc,expected", test_hashes)
def test_jdonldChecksum(doc, expected):
    L = logging.getLogger('test_jsonldChecksum')
    res = opersist.rdfutils.normalizeSONamespace(doc)
    res = opersist.rdfutils.normalizeJSONLDStructure(res)
    #L.info("Normalized: %s", json.dumps(res, indent=2))
    hashes, _ = opersist.utils.jsonChecksums(res)
    #L.info("Hashes = %s", json.dumps(hashes, indent=2))
    assert hashes["sha256"] == expected["sha256"]
