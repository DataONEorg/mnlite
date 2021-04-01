import os
import re
import json
import logging
import flask
import click
import sqlalchemy
import sqlalchemy.orm
import opersist
import opersist.utils
import opersist.models

m_node = flask.Blueprint("m_node", __name__, template_folder="templates/mnode")

XML_TYPE = "text/xml"
PAGE_SIZE = 100

DEFAULT_NODE_CONFIG = {
    "node": {
        "node_id": None,
        "state": "up",
        "name": None,
        "description": None,
        "base_url": None,
        "schedule": {
            "hour": "*",
            "day": "*",
            "min": "0,10,20,30,40,50",
            "mon": "*",
            "sec": "5",
            "wday": "*",
            "year": "*",
        },
        "subject": None,
        "contact_subject": None,
    },
    "content_database": "sqlite:///content.db",
    "log_database": "sqlite:///eventlog.db",
    "data_folder": "data",
    "created": None,
    "default_submitter": None,
    "default_owner": None,
}


def getMNodeNameFromRequest():
    """
    Get MN name from request URL path

    Returns: node name
    """
    match = re.match(r"/(.*)/v2/", flask.request.url_rule.rule)
    return match.group(1)


def getBaseUrlFromRequest():
    base_url = f"{flask.request.url_root}{getMNodeNameFromRequest()}"
    return base_url


def getNode(config_path):
    if not os.path.exists(config_path):
        return None
    node_config = json.load(open(config_path, "r"))
    if node_config["node"].get("base_url", None) is None:
        try:
            node_config["node"]["base_url"] = getBaseUrlFromRequest()
        except:
            pass
    return node_config


def getPersistence(abs_path, node_config):
    op = opersist.OPersist(
        abs_path, db_url=node_config["content_database"], config_file="node.json"
    )
    op.open()
    return op


@m_node.cli.command("new_node", help="Create a new MNode instance")
@click.argument("mn_name")
def createMNode(mn_name):
    mn_name = mn_name.strip()
    the_app = flask.current_app
    L = the_app.logger
    path_id = 0
    node_root_paths = the_app.config.get(
        "NODE_ROOTS",
        [
            "nodes",
        ],
    )
    config_path = os.path.join(the_app.instance_path, node_root_paths[path_id], mn_name)
    if os.path.exists(os.path.join(config_path, "node.json")):
        L.error(
            "Node config %s already exists. Remove before creating.",
            os.path.join(config_path, "node.json"),
        )
        return
    L.info("Creating instance in %s", config_path)
    os.makedirs(config_path, exist_ok=True)
    config_name = os.path.join(config_path, "node.json")
    cfg = DEFAULT_NODE_CONFIG
    cfg["node"]["node_id"] = f"urn:node:{mn_name}"
    cfg["node"]["name"] = f"Unnamed member node: {mn_name}"
    cfg["node"]["description"] = "No description available for this node."
    cfg["created"] = opersist.utils.datetimeToJsonStr(opersist.utils.dtnow())
    with open(config_name, "w") as config_dest:
        config_dest.write(json.dumps(cfg, indent="  "))
    op = getPersistence(config_path, cfg)
    op.close()
    L.info("New node %s created at %s", mn_name, config_path)


"""
def getMNodeConfig(mn_name=None):
    if mn_name is None:
        mn_name = getMNodeNameFromRequest()
    mn_config = flask.current_app.config["m_nodes"].get(mn_name, None)
    return mn_config


def _getConfig(mn_name):
    config = getMNodeConfig(mn_name)
    if config is None:
        names = ",".join(flask.current_app.config["m_nodes"].keys())
        msg = f"Unknown mn_name: {mn_name}. \nAvailable node names: {names}"
        raise (ValueError(msg))
    return config

def setupDB(config_path):
    config = json.load(open(config_path, "r"))
    db_url = config.get("content_database")
    with util.pushd(os.path.dirname(config_path)):
        engine = opersist.models.getEngine(db_url)
        # session here is an instance of sqlalchemy.orm.scoped_session
        session = opersist.models.getSession(engine)
    return (engine, session)


def _computeMd5Sha1(fname):
    BLOCKSIZE = 65536
    sha = hashlib.sha1()
    md5 = hashlib.md5()
    with open(fname, 'rb') as fsrc:
        fb = fsrc.read(BLOCKSIZE)
        while len(fb) > 0:
            sha.update(fb)
            md5.update(fb)
            fb = fsrc.read(BLOCKSIZE)
    return md5.hexdigest(), sha.hexdigest()



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
def listAcces(mn_name):
    L = flask.current_app.logger
    conf = _getConfig(mn_name)
    db = conf["db_session"]
    for policy in db.query(models.AccessPolicy).all():
        print(policy)


@m_node.cli.command("new_access", help="Create new access policy for mn_name")
@click.argument("mn_name")
@click.argument("permission")
@click.argument("subject_id")
def newAccess(mn_name, permission, subject_id):
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
def listObjects(mn_name):
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
def newObject(
    mn_name, identifier, fname, formatid, sid, submitter_id, owner_id, access_id
):
    L = flask.current_app.logger
    conf = _getConfig(mn_name)
    db = conf["db_session"]
    if identifier.find(" ") >= 0:
        raise ValueError(f"Invalid identifier: '{identifier}'")
    if not os.path.exists(fname):
        raise ValueError(f"File not found: {fname}")
    content_fname = None
    checksum_sha256 = None
    with open(fname, "rb") as f_content:
        fstash = flob.FLOB(conf.get("data_folder", "data"))
        fldr, checksum_sha256, content_fname = fstash.addFile(f_content)
    size_bytes = os.stat(content_fname).st_size
    date_added = util.dtnow()
    date_content_modified = date_added
    date_modified = date_added
    date_uploaded = date_added
    node_id = conf["node_id"]
    checksum_md5, checksum_sha1 = _computeMd5Sha1(content_fname)
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
            "checksum_sha256": checksum_sha256,
            "content": content_fname,
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
"""

# == Subject Management ==
# @m_node.cli.command("subjects", help="List subjects registered with mn_name")
# @click.argument("mn_name")
# def listSubjects(mn_name):
#    L = flask.current_app.logger
#    conf = _getConfig(mn_name)
#    db = conf["db_session"]
#    for subject in db.query(models.Subject).all():
#        print(subject)

# Instance management
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


@m_node.before_request
def mnodeBeforeRequest():
    """
    Opens the persistence store for the mnode associated with request.

    Call this before trying to use anything that uses the
    persistence store (database or disk).
    """
    L = flask.current_app.logger
    L.debug("mnodeBeforeRequest rule=%s", flask.request.url_rule.rule)
    flask.g.mn_name = getMNodeNameFromRequest()
    #L.debug("Got mn_name = %s", flask.g.mn_name)
    flask.g.mn_config = flask.current_app.config["m_nodes"].get(flask.g.mn_name, None)
    if flask.g.mn_config is not None:
        flask.g.op = flask.g.mn_config["persistence"]
        flask.g.op.open()
    else:
        L.error("No configuration for mnode = %s", flask.g.mn_name)


@m_node.after_request
def mnodeAfterRequest(response):
    """
    Closes the persistence layer associated with this mnode request

    Args:
        response: The response

    Returns:
        The response
    """
    L = flask.current_app.logger
    L.debug("mnodeAfterRequest")
    if "op" in flask.g:
        try:
            flask.g.op.close()
        except Exception as e:
            L.error(e)
    return response


def d1_exception(name, error_code, detail_code, description, pid=None, trace=None):
    # match = re.match(r"/(.*)/v2/", flask.request.url_rule.rule)
    # node_id = f"urn:node:{match.group(1)}"
    node_id = flask.g.mn_config["node_id"]
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
    # mn_config = getMNodeConfig()
    L.debug("MN CONFIG = %s", flask.g.mn_config)
    try:
        node = getNode(flask.g.mn_config["config"])["node"]
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
    params = {}
    response = flask.make_response(flask.render_template("mnode/index.html", **params))
    return response, 200


@m_node.route("/_page", methods=["GET", "HEAD"])
def _page():
    L = flask.current_app.logger
    from_date = opersist.utils.datetimeFromSomething(
        flask.request.args.get("fromDate", None)
    )
    to_date = opersist.utils.datetimeFromSomething(
        flask.request.args.get("toDate", None)
    )
    identifier = flask.request.args.get("identifier", None)
    format_id = flask.request.args.get("formatId", None)
    replica_status = flask.request.args.get("replicaStatus", None)
    
    _filter = {"field":None, "op": None, "val": None}
    _filter["field"] = flask.request.args.get("filters[0][field]", None)
    _filter["op"] = flask.request.args.get("filters[0][type]", None)
    _filter["val"] = flask.request.args.get("filters[0][value]", None)
    L.info("FILTERS = %s", json.dumps(_filter, indent=2))
    page = 1
    try:
        page = int(flask.request.args.get("page", 1))
    except ValueError as e:
        return d1_InvalidRequest(
            detail_code=1540, description="start must be integer", trace=str(e)
        )
    try:
        count = int(flask.request.args.get("size", PAGE_SIZE))
    except ValueError as e:
        return d1_InvalidRequest(
            detail_code=1540, description="count must be integer", trace=str(e)
        )
    if replica_status is not None:
        return d1_NotImplemented(
            description="Replica status not supported", detail_code=1561
        )
    start = (page-1)*count
    if start < 0:
        start = 0
    if count > PAGE_SIZE:
        count = PAGE_SIZE

    columns = [
        "identifier",
        "checksum_md5",
        "date_modified",
        "size_bytes",
        "format_id",
        "source",
    ]
    db = flask.g.op.getSession()
    olist = db.query(opersist.models.thing.Thing).options(
        sqlalchemy.orm.load_only(*columns)
    )
    if _filter["field"] is not None:
        identifier = _filter["val"]
    if from_date is not None:
        olist = olist.filter(opersist.models.thing.Thing.date_modified >= from_date)
    if to_date is not None:
        olist = olist.filter(opersist.models.thing.Thing.date_modified < to_date)
    if identifier is not None:
        olist = olist.filter(
            sqlalchemy.or_(
                opersist.models.thing.Thing.identifier.like(identifier + "%"),
                opersist.models.thing.Thing.series_id.like(identifier + "%"),
            )
        )
    if format_id is not None:
        olist = olist.filter(
            opersist.models.thing.Thing.format_id.like(format_id + "%")
        )
    total_records = olist.count()
    records = olist.order_by(opersist.models.thing.Thing.date_modified.desc())[
        start : start + count
    ]
    last_page = total_records / count
    return flask.jsonify({"last_page":last_page, "data":[r.asJsonDict() for r in records],"total_rows":total_records})



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
    from_date = opersist.utils.datetimeFromSomething(
        flask.request.args.get("fromDate", None)
    )
    to_date = opersist.utils.datetimeFromSomething(
        flask.request.args.get("toDate", None)
    )
    event = flask.request.args.get("event", None)
    id_filter = flask.request.args.get("idFilter", None)
    start = flask.request.args.get("start", None)
    count = flask.request.args.get("count", None)
    msg = f"getLogRecords: {from_date} {to_date} {event} {id_filter} {start} {count}"
    L.debug("params = %s", msg)
    # TODO: implement getLogRecords
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
    try:
        node = getNode(flask.g.mn_config["config"])["node"]
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
    # TODO: implement describe
    L = flask.current_app.logger
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
    from_date = opersist.utils.datetimeFromSomething(
        flask.request.args.get("fromDate", None)
    )
    to_date = opersist.utils.datetimeFromSomething(
        flask.request.args.get("toDate", None)
    )
    identifier = flask.request.args.get("identifier", None)
    format_id = flask.request.args.get("formatId", None)
    replica_status = flask.request.args.get("replicaStatus", None)
    try:
        start = int(flask.request.args.get("start", 0))
    except ValueError as e:
        return d1_InvalidRequest(
            detail_code=1540, description="start must be integer", trace=str(e)
        )
    try:
        count = int(flask.request.args.get("count", PAGE_SIZE))
    except ValueError as e:
        return d1_InvalidRequest(
            detail_code=1540, description="count must be integer", trace=str(e)
        )
    if replica_status is not None:
        return d1_NotImplemented(
            description="Replica status not supported", detail_code=1561
        )
    if start < 0:
        start = 0
    if count > PAGE_SIZE:
        count = PAGE_SIZE

    columns = [
        "identifier",
        "checksum_md5",
        "date_modified",
        "size_bytes",
        "format_id",
    ]
    db = flask.g.op.getSession()
    olist = db.query(opersist.models.thing.Thing).options(
        sqlalchemy.orm.load_only(*columns)
    )
    if from_date is not None:
        olist = olist.filter(opersist.models.thing.Thing.date_modified >= from_date)
    if to_date is not None:
        olist = olist.filter(opersist.models.thing.Thing.date_modified < to_date)
    if identifier is not None:
        olist = olist.filter(
            sqlalchemy.or_(
                opersist.models.thing.Thing.identifier.like(identifier + "%"),
                opersist.models.thing.Thing.series_id.like(identifier + "%"),
            )
        )
    if format_id is not None:
        olist = olist.filter(
            opersist.models.thing.Thing.format_id.like(format_id + "%")
        )
    total_records = olist.count()
    records = olist.order_by(opersist.models.thing.Thing.date_modified.desc())[
        start : start + count
    ]
    return flask.Response(
        streamTemplate(
            "mnode/objectlist_template.xml",
            records_count=len(records),
            records_start=start,
            records_total=total_records,
            records=records,
        ),
        content_type=XML_TYPE,
    )


# get
@m_node.route(
    "/object",
    methods=[
        "GET",
    ],
)
def _listObjects():
    L = flask.current_app.logger
    db = flask.g.op.getSession()
    return listObjects(db)

@m_node.route("/object/<path:identifier>", strict_slashes=False)
def getObject(identifier):
    L = flask.current_app.logger
    db = flask.g.op.getSession()
    if identifier is None:
        return listObjects(db)
    obj = flask.g.op.getThingPIDorSID(identifier)
    if obj is None:
        return d1_NotFound(pid=identifier, detail_code=1002)
    response = flask.make_response(obj.content)
    response.mimetype = obj.media_type_name
    obj_path = flask.g.op.contentAbsPath(obj.content)
    fldr = os.path.dirname(obj_path)
    fname = os.path.basename(obj_path)
    return flask.send_from_directory(
        fldr,
        fname,
        mimetype=obj.media_type_name,
        as_attachment=True,
        attachment_filename=obj.file_name,
        last_modified=obj.t_content_modified,
    )


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
    # db = flask.g.op.getSession()
    obj = flask.g.op.getThingPIDorSID(identifier)
    if obj is None:
        return d1_NotFound(pid=identifier, detail_code=1041)
    sysm = obj.asJsonDict()
    sysm["checksum_algorithm"] = "MD5"
    sysm["checksum"] = obj.checksum_md5
    if sysm["format_id"] is None:
        sysm["format_id"] = "application/octet-stream"
    if sysm["origin_member_node"] is None:
        sysm["origin_member_node"] = flask.g.mn_config["node_id"]
    if sysm["authoritative_member_node"] is None:
        sysm["authoritative_member_node"] = flask.g.mn_config["node_id"]
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
    date_modified = opersist.utils.datetimeFromSomething(
        flask.request.files.get("dateSysMetaLastModified", None)
    )
    msg = f"serial_version: {serial_version} date_modified: {date_modified}"
    return d1_NotImplemented(
        description="getReplica", detail_code=1330, pid=identifier, trace=msg
    )
