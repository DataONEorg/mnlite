import os
import pathlib
import flask
import flask_monitoringdashboard
from . import mnode


def create_app(test_config=None):
    app = flask.Flask(__name__, instance_relative_config=True)
    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    flask_monitoringdashboard.config.init_from(
        file=os.path.join(app.instance_path, "dashboard/dashboard.cfg")
    )
    flask_monitoringdashboard.bind(app)
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
    for node_root in node_root_paths:
        node_path = pathlib.Path(os.path.join(app.instance_path, node_root))
        for path in node_path.iterdir():
            if path.is_dir():
                mn_name = path.name.lower()
                mn_config = {
                    "config": os.path.abspath(
                        os.path.join(path.absolute(), "node.json")
                    ),
                    "node_id": None,
                    "db_engine": None,
                    "db_session": None,
                }
                options = {"mnode_name": mn_name, "config_path": mn_config["config"]}
                app.register_blueprint(
                    mnode.m_node, url_prefix=f"/{mn_name}/v2", **options
                )
                node_info = mnode.getNode(mn_config["config"])
                mn_config["node_id"] = node_info["node_id"]
                db_engine, db_session = mnode.setupDB(mn_config["config"])
                mn_config["db_engine"] = db_engine
                mn_config["db_session"] = db_session
                app.config["m_nodes"][mn_name] = mn_config

    @app.route("/")
    def inventory():
        nodes = []
        for mn_name, mn_config in app.config["m_nodes"].items():
            nodes.append(
                {
                    "name": mn_name,
                    "node_id": mn_config["node_id"],
                    "config": mn_config["config"],
                }
            )
        return flask.render_template("index.html", nodes=nodes)

    return app
