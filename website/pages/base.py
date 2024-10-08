from fastapi.templating import Jinja2Templates

from website.constants import WEBSITE_DIR


COMPONENTS = Jinja2Templates(directory=WEBSITE_DIR/"components")
TEMPLATES = Jinja2Templates(directory=WEBSITE_DIR/"templates")
