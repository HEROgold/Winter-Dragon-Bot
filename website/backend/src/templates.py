from fastapi.templating import Jinja2Templates
from jinja2 import Template
from pages.base import COMPONENTS


templates = Jinja2Templates(directory="website/templates")

head: Template = COMPONENTS.get_template("head.j2")
header: Template = COMPONENTS.get_template("header.j2")
nav: Template = COMPONENTS.get_template("nav.j2")
footer: Template = COMPONENTS.get_template("footer.j2")
