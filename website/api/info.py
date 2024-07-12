from website.app import app


@app.get("/args")
def post_all() -> str:
    """
    Debug route that prints all request data.
    """
    return f"{request.args=}"
