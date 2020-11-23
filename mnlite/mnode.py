import os
import re
import json
import flask
import datetime
import dateparser

m_node = flask.Blueprint("m_node", __name__, template_folder="templates")

XML_TYPE = "text/xml"


def datetimeFromSomething(V):
    if V is None:
        return None
    if isinstance(V, datetime.datetime):
        return V
    if isinstance(V, float) or isinstance(V, int):
        # asumes this is a timestamp
        return datetime.datetime.fromtimestamp(V, tz=datetime.timezone.utc)
    if isinstance(V, str):
        return dateparser.parse(
            V, settings={"TIMEZONE": "+0000", "RETURN_AS_TIMEZONE_AWARE": True}
        )
    return None


def getUrlPrefixFromRequest(request):
    match = re.match(r"/(.*/)v2/", flask.request.url_rule.rule)
    return match.group(1)


def getBaseUrlFromRequest(request):
    base_url = f"{flask.request.url_root}{getUrlPrefixFromRequest(request)}"
    return base_url


def getNodeFolder(request):
    node_folder = os.path.join(
        flask.current_app.instance_path, "nodes", getUrlPrefixFromRequest(request)
    )
    return node_folder


def getNodeFromRequest(request):
    node_file = os.path.join(getNodeFolder(request), "node.json")
    config = json.load(open(node_file, "r"))
    node = config["node"]
    if node.get("base_url", None) is None:
        node["base_url"] = getBaseUrlFromRequest(request)
    return node


def d1_exception(name, error_code, detail_code, description, pid=None, trace=None):
    match = re.match(r"/(.*/)v2/", flask.request.url_rule.rule)
    node_id = f"{flask.request.url_root}{match.group(1)}"
    params = {
        "name": name,
        "error_code": error_code,
        "detail_code": detail_code,
        "description": description,
        "pid": pid,
        "trace_information": trace,
        "node_id": node_id,
    }
    response = flask.make_response(
        flask.render_template("error_template.xml", **params)
    )
    response.mimetype = XML_TYPE
    return response, error_code


def d1_NotImplemented(
    detail_code=0, description="Not implemented", pid=None, trace=None
):
    return d1_exception(
        "NotImplemented", 501, detail_code, description, pid=pid, trace=trace
    )


def d1_InvalidRequest(
    detail_code=0, description="Invalid request", pid=None, trace=None
):
    return d1_exception(
        "InvalidRequest", 400, detail_code, description, pid=pid, trace=trace
    )


def d1_NotFound(detail_code=0, description="Not found", pid=None, trace=None):
    return d1_exception("NotFound", 404, detail_code, description, pid=pid, trace=trace)


def d1_ServiceFailure(
    detail_code=0, description="Service failure", pid=None, trace=None
):
    return d1_exception(
        "ServiceFailure", 500, detail_code, description, pid=pid, trace=trace
    )


# == Core API ==
# https://dataone-architecture-documentation.readthedocs.io/en/latest/apis/MN_APIs.html#core-api


def getCapabilitiesImpl():
    try:
        node = getNodeFromRequest(flask.request)
        schedule = node["schedule"]
        response = flask.make_response(
            flask.render_template("node_template.xml", mnode=node, schedule=schedule)
        )
        response.mimetype = XML_TYPE
        return response, 200
    except Exception as e:
        return d1_ServiceFailure(
            detail_code=2162, description="getCapabilities", trace=e
        )


@m_node.route(
    "/",
    methods=[
        "HEAD",
        "GET",
    ],
)
def default():
    return getCapabilitiesImpl()


@m_node.route(
    "/node",
    methods=[
        "HEAD",
        "GET",
    ],
)
def getCapabilities():
    return getCapabilitiesImpl()


@m_node.route(
    "/log",
    methods=[
        "HEAD",
        "GET",
    ],
)
def getLogRecords():
    from_date = datetimeFromSomething(flask.request.args.get("fromDate", None))
    to_date = datetimeFromSomething(flask.request.args.get("toDate", None))
    event = flask.request.args.get("event", None)
    id_filter = flask.request.args.get("idFilter", None)
    start = flask.request.args.get("start", None)
    count = flask.request.args.get("count", None)
    msg = f"getLogRecords: {from_date} {to_date} {event} {id_filter} {start} {count}"
    return d1_NotImplemented(description="getLogRecords", detail_code=1461, trace=msg)


@m_node.route(
    "/monitor/ping",
    methods=[
        "HEAD",
        "GET",
    ],
)
def monitorPing():
    # return d1_NotImplemented(description="ping", detail_code=2041)
    try:
        node = getNodeFromRequest(flask.request)
        schedule = node["schedule"]
        response = flask.make_response(
            flask.render_template("ping_template.html", mnode=node)
        )
        return response, 200
    except Exception as e:
        return d1_ServiceFailure(detail_code=2042, description="ping", trace=e)


# == Read API ==
# https://dataone-architecture-documentation.readthedocs.io/en/latest/apis/MN_APIs.html#read-api

# describe
@m_node.route(
    "/object/<path:identifier>",
    methods=[
        "HEAD",
    ],
)
def describe(identifier):
    return d1_NotImplemented(description="describe", detail_code=1361, pid=identifier)


# listObjects
def listObjects():
    from_date = datetimeFromSomething(flask.request.args.get("fromDate", None))
    to_date = datetimeFromSomething(flask.request.args.get("toDate", None))
    identifier = flask.request.args.get("identifier", None)
    format_id = flask.request.args.get("formatId", None)
    replica_status = flask.request.args.get("replicaStatus", None)
    start = flask.request.args.get("start", None)
    count = flask.request.args.get("count", None)
    msg = f"listObjects: {from_date} {to_date} {identifier} {format_id} {replica_status} {start} {count}"
    return d1_NotImplemented(description="listObjects", detail_code=1561, trace=msg)


# get
@m_node.route(
    "/object",
    defaults={"identifier": None},
    methods=[
        "GET",
    ],
)
@m_node.route(
    "/object/",
    defaults={"identifier": None},
    methods=[
        "GET",
    ],
)
@m_node.route("/object/<path:identifier>")
def getObject(identifier):
    if identifier is None:
        return listObjects()
    return d1_NotImplemented(description="get", detail_code=1001, pid=identifier)


# getChecksum
@m_node.route(
    "/checksum/<path:identifier>",
    methods=[
        "GET",
    ],
)
def getChecksum(identifier):
    checksum_algorithm = flask.request.args.get("checksumAlgorithm", None)
    msg = f"checksum_algorithm: {checksum_algorithm}"
    return d1_NotImplemented(
        description="getChecksum", detail_code=1401, pid=identifier, trace=msg
    )


# getReplica
@m_node.route(
    "/replica/<path:identifier>",
    methods=[
        "GET",
    ],
)
def getReplica(identifier):
    return d1_NotImplemented(description="getReplica", detail_code=2180, pid=identifier)


# getSystemMetadata
@m_node.route(
    "/meta/<path:identifier>",
    methods=[
        "GET",
    ],
)
def getMeta(identifier):
    return d1_NotImplemented(
        description="getSystemMetadata", detail_code=1041, pid=identifier
    )


# synchronizationFailed
@m_node.route(
    "/error",
    methods=[
        "POST",
    ],
)
def synchronizationFailed():
    message = flask.request.files.get("message", None)
    return d1_NotImplemented(description="getReplica", detail_code=2160, trace=message)


# systemMetadataChanged
@m_node.route(
    "/dirtySystemMetadata",
    methods=[
        "POST",
    ],
)
def systemMetadataChanged():
    identifier = flask.request.files.get("id", None)
    serial_version = flask.request.files.get("serialVersion", None)
    date_modified = datetimeFromSomething(flask.request.files.get("dateSysMetaLastModified", None))
    msg = f"serial_version: {serial_version} date_modified: {date_modified}"
    return d1_NotImplemented(
        description="getReplica", detail_code=1330, pid=identifier, trace=msg
    )
