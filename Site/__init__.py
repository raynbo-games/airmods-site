import os, logging
from flask import Flask
from flask.cli import load_dotenv
from authlib.integrations.flask_client import OAuth

load_dotenv()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.logger.setLevel(logging.INFO)
    app.url_map.strict_slashes = False
    oauth = OAuth(app)
    google = oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY'),
        DATABASE_URL = os.environ.get('DATABASE_URL'),
        GOOGLE = google,
    )

    os.makedirs(app.instance_path, exist_ok=True)

    import Site.code.main.root as root
    app.register_blueprint(root.bp)

    import Site.code.airspy.main as airspy
    app.register_blueprint(airspy.bp)

    import Site.code.airmods.main as airmods
    app.register_blueprint(airmods.bp)

    import Site.code.auth.main as auth
    app.register_blueprint(auth.bp)

    import Site.code.settings.main as settings
    app.register_blueprint(settings.bp)

    import Site.code.admin.main as admin
    app.register_blueprint(admin.bp)

    import Site.code.community.main as community
    app.register_blueprint(community.bp)

    import Site.code.roadmap.main as roadmap
    app.register_blueprint(roadmap.bp)

    from Site.code.database.main import init_app
    init_app(app)

    from Site.code.context import init_context
    init_context(app)

    from Site.code.tasks import init_tasks
    init_tasks(app)

    return app

app = create_app()