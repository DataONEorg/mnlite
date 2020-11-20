import os
import pathlib
import flask
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

    app._nodes = set()
    node_root_paths = app.config.get(
        "NODE_ROOTS",
        [
            "nodes",
        ],
    )
    for node_root in node_root_paths:
        node_path = pathlib.Path(os.path.join(app.instance_path, node_root))
        for path in node_path.iterdir():
            if path.is_dir():
                app._nodes.add(path.name)
                app.register_blueprint(mnode.m_node, url_prefix=f"/{path.name}/v2")

    @app.route("/")
    def inventory():
        nodes = []
        for node in app._nodes:
            nodes.append({"name": node})
        return flask.render_template("index.html", nodes=nodes)

    return app
