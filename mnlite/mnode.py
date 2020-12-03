import os
import re
import json
import logging
import hashlib
import flask
import click
import sqlalchemy
import sqlalchemy.orm
from . import util
from . import models

m_node = flask.Blueprint("m_node", __name__, template_folder="templates/mnode")

XML_TYPE = "text/xml"
PAGE_SIZE = 100


def _getConfig(mn_name):
    L = flask.current_app.logger
    config = getMNodeConfig(mn_name)
    if config is None:
        names = ",".join(flask.current_app.config["m_nodes"].keys())
        msg = f"Unknown mn_name: {mn_name}. \nAvailable node names: {names}"
        raise (ValueError(msg))
    return config


# == Subject Management ==
@m_node.cli.command("subjects", help="List subjects registered with mn_name")
@click.argument("mn_name")
def newSubject(mn_name):
    L = flask.current_app.logger
    conf = _getConfig(mn_name)
    db = conf["db_session"]
    for subject in db.query(models.Subject).all():
        print(subject)


@m_node.cli.command("new_subject", help="Add a new subject to mn_name")
@click.argument("mn_name")
@click.argument("subject")
def newSubject(mn_name, subject):
    L = flask.current_app.logger
    print(f"new subject: {mn_name} {subject}")
    conf = _getConfig(mn_name)
    db = conf["db_session"]
    res = models.getOrCreate(db, models.Subject, subject=subject)
    L.info("Subject: %s", res)


# == AccessPolicy Management ==
@m_node.cli.command("access", help="List access policies created for mn_name")
@click.argument("mn_name")
def newSubject(mn_name):
    L = flask.current_app.logger
    conf = _getConfig(mn_name)
    db = conf["db_session"]
    for policy in db.query(models.AccessPolicy).all():
        print(policy)


@m_node.cli.command("new_access", help="Create new access policy for mn_name")
@click.argument("mn_name")
@click.argument("permission")
@click.argument("subject_id")
def newSubject(mn_name, permission, subject_id):
    L = flask.current_app.logger
    conf = _getConfig(mn_name)
    db = conf["db_session"]
    permission = permission.lower()
    res = models.getOrCreate(
        db, models.AccessPolicy, permission=permission, subject_id=subject_id
    )
    L.info("Access: %s", res)


# == Content Management ==
@m_node.cli.command("content", help="List content in mn_name")
@click.argument("mn_name")
def newSubject(mn_name):
    L = flask.current_app.logger
    conf = _getConfig(mn_name)
    db = conf["db_session"]
    for content in db.query(models.Content).all():
        print(content)


@m_node.cli.command("new_content", help="Add new object to mn_name")
@click.argument("mn_name")
@click.argument("identifier")
@click.argument("fname")
@click.option("-f", "--formatid", default="application/ld+json")
@click.option("--sid", default=None)
@click.option("--submitter_id", default=1)
@click.option("--owner_id", default=1)
@click.option("--access_id", default=1)
def newSubject(
    mn_name, identifier, fname, formatid, sid, submitter_id, owner_id, access_id
):
    L = flask.current_app.logger
    conf = _getConfig(mn_name)
    db = conf["db_session"]
    if identifier.find(" ") >= 0:
        raise ValueError(f"Invalid identifier: '{identifier}'")
    if not os.path.exists(fname):
        raise ValueError(f"File not found: {fname}")
    bytes = open(fname, "rb").read()
    size_bytes = len(bytes)
    date_added = util.dtnow()
    date_content_modified = date_added
    date_modified = date_added
    date_uploaded = date_added
    node_id = conf["node_id"]
    checksum_md5 = hashlib.md5(bytes).hexdigest()
    checksum_sha1 = hashlib.sha1(bytes).hexdigest()

    # access_policy = db.query(models.AccessPolicy).get(access_id)
    # L.debug(access_policy)

    res = models.addContent(
        db,
        {
            "identifier": identifier,
            "authoritative_member_node": node_id,
            "size_bytes": size_bytes,
            "date_added": date_added,
            "date_content_modified": date_content_modified,
            "checksum_md5": checksum_md5,
            "checksum_sha1": checksum_sha1,
            "content": bytes.decode(encoding="utf-8"),
            "format_id": formatid,
            "date_modified": date_modified,
            "serial_version": 1,
            "series_id": sid,
            "date_uploaded": date_uploaded,
            "origin_member_node": node_id,
            "media_type_name": formatid,
            "file_name": os.path.basename(fname),
            "submitter_id": submitter_id,
            "rights_holder_id": owner_id,
        },
    )
    L.info("content: %s", res)


def setupDB(config_path):
    config = json.load(open(config_path, "r"))
    db_url = config.get("content_database")
    with util.pushd(os.path.dirname(config_path)):
        engine = models.getEngine(db_url)
        session = models.getSession(engine)
    return (engine, session)


@m_node.record
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


def getMNodeNameFromRequest():
    match = re.match(r"/(.*)/v2/", flask.request.url_rule.rule)
    return match.group(1)


def getMNodeConfig(mn_name=None):
    L = flask.current_app.logger
    if mn_name is None:
        mn_name = getMNodeNameFromRequest()
    mn_config = flask.current_app.config["m_nodes"].get(mn_name, None)
    return mn_config


def getBaseUrlFromRequest():
    base_url = f"{flask.request.url_root}{getMNodeNameFromRequest()}"
    return base_url


def getNode(config_path):
    node_config = json.load(open(config_path, "r"))
    node = node_config["node"]
    if node.get("base_url", None) is None:
        try:
            node["base_url"] = getBaseUrlFromRequest()
        except:
            pass
    return node


def getContentDB(mn_name=None):
    config = getMNodeConfig(mn_name=mn_name)
    return config.get("db_session")


def d1_exception(name, error_code, detail_code, description, pid=None, trace=None):
    match = re.match(r"/(.*)/v2/", flask.request.url_rule.rule)
    node_id = f"urn:node:{match.group(1)}"
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
    L = flask.current_app.logger
    mn_config = getMNodeConfig()
    L.debug("MN CONFIG = %s", mn_config)
    try:
        node = getNode(mn_config["config"])
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
    L = flask.current_app.logger
    from_date = util.datetimeFromSomething(flask.request.args.get("fromDate", None))
    to_date = util.datetimeFromSomething(flask.request.args.get("toDate", None))
    event = flask.request.args.get("event", None)
    id_filter = flask.request.args.get("idFilter", None)
    start = flask.request.args.get("start", None)
    count = flask.request.args.get("count", None)
    msg = f"getLogRecords: {from_date} {to_date} {event} {id_filter} {start} {count}"
    L.debug("params = %s", msg)
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
    L = flask.current_app.logger
    mn_config = getMNodeConfigFromRequest()
    try:
        node = getNode(mn_config["config"])
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
    L = flask.current_app.logger
    db = flask.current_app.config.get("m_node.db")
    return d1_NotImplemented(description="describe", detail_code=1361, pid=identifier)


def streamTemplate(template_name, **context):
    flask.current_app.update_template_context(context)
    t = flask.current_app.jinja_env.get_template(template_name)
    res = t.stream(context)
    res.disable_buffering()
    return res


# listObjects
def listObjects(db):
    L = flask.current_app.logger
    from_date = util.datetimeFromSomething(flask.request.args.get("fromDate", None))
    to_date = util.datetimeFromSomething(flask.request.args.get("toDate", None))
    identifier = flask.request.args.get("identifier", None)
    format_id = flask.request.args.get("formatId", None)
    replica_status = flask.request.args.get("replicaStatus", None)
    try:
        start = int(flask.request.args.get("start", 0))
    except ValueError as e:
        return d1_InvalidRequest(detail_code=1540, description="start must be integer", trace=str(e))
    try:
        count = int(flask.request.args.get("count", PAGE_SIZE))
    except ValueError as e:
        return d1_InvalidRequest(detail_code=1540, description="count must be integer", trace=str(e))
    if replica_status is not None:
        return d1_NotImplemented(
            description="Replica status not supported", detail_code=1561
        )
    if start < 0:
        start = 0
    if count > PAGE_SIZE:
        count = PAGE_SIZE

    columns = ["identifier", "format_id", "checksum_md5", "date_modified", "size_bytes"]
    db = getContentDB()
    olist = db.query(models.Content).options(sqlalchemy.orm.load_only(*columns))
    if from_date is not None:
        olist = olist.filter(models.Content.date_modified >= from_date)
    if to_date is not None:
        olist = olist.filter(models.Content.date_modified < to_date)
    if identifier is not None:
        olist = olist.filter(
            sqlalchemy.or_(
                models.Content.identifier.like(identifier + "%"),
                models.Content.series_id.like(identifier + "%"),
            )
        )
    if format_id is not None:
        olist = olist.filter(models.Content.format_id.like(format_id + "%"))
    total_records = olist.count()
    records = olist.order_by(models.Content.date_modified)[start : start + count]
    return flask.Response(
        streamTemplate(
            "mnode/objectlist_template.xml",
            records_count=len(records),
            records_start=start,
            records_total=total_records,
            records=records,
        ),
        content_type=XML_TYPE
    )


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
    L = flask.current_app.logger
    db = getContentDB()
    if identifier is None:
        return listObjects(db)
    obj = db.query(models.Content).get(identifier)
    if obj is None:
        return d1_NotFound(pid=identifier, detail_code=1002)
    response = flask.make_response(obj.content)
    response.mimetype = obj.media_type_name
    return response, 200


# getChecksum
@m_node.route(
    "/checksum/<path:identifier>",
    methods=[
        "GET",
    ],
)
def getChecksum(identifier):
    L = flask.current_app.logger
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
    L = flask.current_app.logger
    return d1_NotImplemented(description="getReplica", detail_code=2180, pid=identifier)


# getSystemMetadata
@m_node.route(
    "/meta/<path:identifier>",
    methods=[
        "GET",
    ],
)
def getMeta(identifier):
    L = flask.current_app.logger
    db = getContentDB()
    obj = db.query(models.Content).get(identifier)
    if obj is None:
        return d1_NotFound(pid=identifier, detail_code=1041)
    sysm = obj.asJsonDict()
    sysm["checksum_algorithm"] = "MD5"
    sysm["checksum"] = obj.checksum_md5
    response = flask.make_response(
        flask.render_template("systemmetadata_template.xml", sysm=sysm)
    )
    response.mimetype = XML_TYPE
    return response


# synchronizationFailed
@m_node.route(
    "/error",
    methods=[
        "POST",
    ],
)
def synchronizationFailed():
    L = flask.current_app.logger
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
    L = flask.current_app.logger
    identifier = flask.request.files.get("id", None)
    serial_version = flask.request.files.get("serialVersion", None)
    date_modified = util.datetimeFromSomething(
        flask.request.files.get("dateSysMetaLastModified", None)
    )
    msg = f"serial_version: {serial_version} date_modified: {date_modified}"
    return d1_NotImplemented(
        description="getReplica", detail_code=1330, pid=identifier, trace=msg
    )
