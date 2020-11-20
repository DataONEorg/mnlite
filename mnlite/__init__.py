import os
import flask
from . import mnode

def create_app(test_config=None):
    app = flask.Flask(__name__, instance_relative_config=True)
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app.register_blueprint(mnode.m_node, url_prefix='/mn_1/v2')
    app.register_blueprint(mnode.m_node, url_prefix='/mn_2/v2')

    @app.route('/')
    def inventory():
        return "Inventory."

    return app

