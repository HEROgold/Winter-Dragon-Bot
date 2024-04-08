from flask import Flask

from blueprints import ctrl, docs, page
from tools.config_reader import STATIC_PATH, TEMPLATE_PATH, config
from tools.flask_tools import register_blueprints


app = Flask(__name__, template_folder=TEMPLATE_PATH, static_folder=STATIC_PATH)
app.logger.setLevel(config["Main"]["log_level"])
register_blueprints(app, [ctrl, docs, page])
