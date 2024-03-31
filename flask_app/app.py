from flask import Flask

from flask_app.blueprints import ctrl, docs, page
from tools.flask_tools import register_blueprints


app = Flask(__name__)
register_blueprints(app, [ctrl, docs, page])
