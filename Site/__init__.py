import os
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
    )

    import Site.code.root as root
    app.register_blueprint(root.bp)

    return app

app = create_app()