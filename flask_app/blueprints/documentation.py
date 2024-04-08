from flask import Blueprint, render_template


bp = Blueprint("documentation", __name__)


@bp.route("/docs")
async def docs() -> str:
    return render_template("docs.j2")
