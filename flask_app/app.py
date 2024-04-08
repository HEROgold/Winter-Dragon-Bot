from flask import Flask

from tools.flask_tools import register_blueprints

from .blueprints import ctrl, docs, page


app = Flask(__name__)

register_blueprints(app, [ctrl, docs, page])
