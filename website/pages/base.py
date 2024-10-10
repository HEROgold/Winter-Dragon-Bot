from fastapi.templating import Jinja2Templates

from website.constants import WEBSITE_DIR


TEMPLATES_DIR = WEBSITE_DIR/"templates"
COMPONENTS_DIR = TEMPLATES_DIR/"components"
STATIC_DIR = WEBSITE_DIR/"static"

TEMPLATES = Jinja2Templates(directory=TEMPLATES_DIR)
COMPONENTS = Jinja2Templates(directory=COMPONENTS_DIR)
