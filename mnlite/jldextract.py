'''
Extract JSON-LD
'''
import logging
import flask
import pyld
import requests
import json
import opersist.utils
import opersist.rdfutils

jldex = flask.Blueprint("jldex", __name__, template_folder="templates/jldex")

def loadJsonLD(url):
    response = requests.get(url)
    jsonld = pyld.jsonld.load_html(
        response.content,
        response.url,
        profile=None,
        options={"extractAllScripts": True}
    )
    return jsonld

@jldex.record
def record(state):
    """
    Called when a m_node blueprint is being registered.
    Args:
        state: The state information for the BluePrint

    Returns: nothing

    """
    L = logging.getLogger("m_node.record")
    name = state.options.get("mnode_name")
    L.debug("MNODE name = %s", name)


@jldex.route(
    "/",
    methods=[
        "HEAD",
        "GET",
    ],
)
def default():
    url = flask.request.args.get("url",None)
    context = {
        "@context": {
            "@vocab": "http://schema.org/"
        }
    }
    force_lists = [
        "http://schema.org/identifier",
        "http://schema.org/creator",
    ]
    data = {
        "url": url,
        "jsonld":None,
        "jsonld_ns": None,
        "jsonld_st": None,
        "ids": None,
        "hashes": None,
        "bytes":None,
    }
    if not url is None:
        jsonld = loadJsonLD(url)
        data["jsonld"] = json.dumps(jsonld, indent=2)
        jsonld_ns = opersist.rdfutils.normalizeSONamespace(jsonld)
        data["jsonld_ns"] = json.dumps(jsonld_ns, indent=2)
        jsonld_st = opersist.rdfutils.normalizeJSONLDStructure(jsonld_ns, base=url, context=context, force_lists=force_lists)
        data["jsonld_st"] = json.dumps(jsonld_st, indent=2)
        ids = opersist.rdfutils.extractIdentifiers(jsonld_st)
        data["ids"] = json.dumps(ids, indent=2)
        hashes, b = opersist.utils.jsonChecksums(jsonld_st)
        data["hashes"] = json.dumps(hashes, indent=2)
        data["bytes"] = b.decode()
    response = flask.make_response(
        flask.render_template("jldex.html", data=data)
    )
    return response, 200

