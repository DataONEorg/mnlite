import os
import pathlib
import json
import flask
import flask_cors
from mnlite import mnode
import opersist.utils

def initialize_instance(instance_path):
    db_path = os.path.join(instance_path, "dashboard")
    db_config = os.path.join(db_path, "dashboard.cfg")
    if not os.path.exists(db_config):
        os.makedirs(db_path)
        with open(db_config, "wt") as cfg:
            cfg.write(
                (
                    "[dashboard]\n"
                    "GIT=/.git/\n\n"
                    "[authentication]\n"
                    "USERNAME=admin\n"
                    "password=admin\n"
                    "SECUTIY_TOKEN=change_me\n\n"
                    "[database]\n"
                    "DATABASE=sqlite:///instance/dashboard/dashboard.db\n\n"
                    "[visualization]\n"
                    "TIMEZONE=UTC\n"
                )
            )


def create_app(test_config=None):
    app = flask.Flask(__name__, instance_relative_config=True)
    flask_cors.CORS(app)
    L = app.logger
    L.info("create_app")
    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    #initialize_instance(app.instance_path)
    #flask_monitoringdashboard.config.init_from(
    #    file=os.path.join(app.instance_path, "dashboard/dashboard.cfg")
    #)
    #flask_monitoringdashboard.bind(app)

    node_root_paths = app.config.get(
        "NODE_ROOTS",
        [
            "nodes",
        ],
    )
    """
    Setup individual MNs using a blueprint for each.
    Configuration ends up as:
    app.config['m_nodes'][node_name]['config']
    """
    app.config["m_nodes"] = {}
    app.url_map.strict_slashes = True
    for node_root in node_root_paths:
        node_path = pathlib.Path(os.path.join(app.instance_path, node_root))
        node_path.mkdir(parents=True, exist_ok=True)
        for path in node_path.iterdir():
            if path.is_dir():
                mn_name = path.name
                L.debug("MN_NAME = %s", mn_name)
                abs_path = path.absolute()
                mn_config = {
                    "config": os.path.abspath(os.path.join(abs_path, "node.json")),
                    "node_id": None,
                    "persistence": None,
                }
                options = {"mnode_name": mn_name, "config_path": mn_config["config"]}
                url_prefix = f"/{mn_name}/v2"
                L.debug("URL PREFIX = %s", url_prefix)
                app.register_blueprint(
                    mnode.m_node, url_prefix=url_prefix, **options
                )
                node_info = mnode.getNode(mn_config["config"])
                if node_info is not None:
                    mn_config["node_id"] = node_info["node"]["node_id"]
                    mn_config["persistence"] = mnode.getPersistence(abs_path, node_info)
                    # The persistence layer is returned open and initialized
                    # Close it since it will be used on a different thread
                    # when services requests
                    mn_config["persistence"].close()

                    # db_engine, db_session = mnode.setupDB(mn_config["config"])
                    # mn_config["db_engine"] = db_engine
                    # mn_config["db_session"] = db_session
                    app.config["m_nodes"][mn_name] = mn_config

    @app.teardown_appcontext
    def shutdownSession(exception=None):
        # L = app.logger
        # L.debug("teardown appcontext")
        #jnius.detach()
        pass

    @app.before_request
    def beforeRequest():
        # L = app.logger
        # L.debug("beforeRequest")
        pass

    @app.teardown_request
    def afterRequest(exception=None):
        # L = app.logger
        # L.debug("afterRequest")
        pass

    @app.template_filter()
    def datetimeToJsonStr(dt):
        return opersist.utils.datetimeToJsonStr(dt)

    @app.template_filter()
    def asjson(jobj):
        if jobj is not None:
            return json.dumps(jobj, indent=2)
        return ""

    @app.route("/")
    def inventory():
        nodes = []
        for mn_name, mn_config in app.config["m_nodes"].items():
            node_info = mnode.getNode(mn_config["config"])
            entry = {
                    "name": mn_name,
                    "node_id": mn_config["node_id"],
                    "config": mn_config["config"],
                    "sitemap": node_info["spider"]["sitemap_urls"][0],
                    "oldest": "",
                    "newest": "",
                    "count": 0
                }
            op = None
            try:
                op = mn_config["persistence"]
                op.open()
                stats = op.basicStatsThings()
                #entry["numrecords"] = op.countThings()
                entry.update(stats)
            except Exception as e:
                app.logger.error(e)
            finally:
                op.close()
            nodes.append(entry)
        return flask.render_template("index.html", nodes=nodes)


    def has_no_empty_params(rule):
        defaults = rule.defaults if rule.defaults is not None else ()
        arguments = rule.arguments if rule.arguments is not None else ()
        return len(defaults) >= len(arguments)


    @app.route("/site-map")
    def site_map():
        links = []
        for rule in app.url_map.iter_rules():
            # Filter out rules we can't navigate to in a browser
            # and rules that require parameters
            if "GET" in rule.methods and has_no_empty_params(rule):
                url = flask.url_for(rule.endpoint, **(rule.defaults or {}))
                links.append((url, rule.endpoint))
        return "<pre>" + json.dumps(links, indent=2) + "</pre>"

    @app.route("/sha256/<sha_256>")
    def getItemBySha256(sha_256):
        #def getPersistence(abs_path, node_config):
        sha_256 = sha_256.replace("sha256:", "")
        for mn_name, mn_config in app.config["m_nodes"].items():
            op = None
            app.logger.info("Item %s from %s", sha_256, mn_name)
            try:
                op = mn_config["persistence"]
                op.open()
                obj = op.getThingSha256(sha_256)
                if obj is not None:
                    response = flask.make_response(obj.content)
                    response.mimetype = obj.media_type_name
                    obj_path = op.contentAbsPath(obj.content)
                    fldr = os.path.dirname(obj_path)
                    fname = os.path.basename(obj_path)
                    return flask.send_from_directory(
                        fldr,
                        fname,
                        mimetype=obj.media_type_name,
                        as_attachment=False,
                        attachment_filename=obj.file_name,
                        last_modified=obj.t_content_modified,
                    )
            except Exception as e:
                app.logger.error(e)
            finally:
                if op is not None:
                    op.close()
        flask.abort(404)


    return app

