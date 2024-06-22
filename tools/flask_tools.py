from flask import Blueprint, Flask


def register_blueprints(app: Flask, blueprints: list[Blueprint]) -> None:
    """Register all blueprints."""
    for blueprint in blueprints:
        app.register_blueprint(blueprint)
