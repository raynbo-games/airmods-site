import os, logging, click
from flask import Flask, session
from flask.cli import load_dotenv
from flask_apscheduler import APScheduler
from Site.code.airspy.processes import tick_airspy, tick_airspy_icons
from Site.code.config import AIRSPY_UPDATE_TIMEOUT, AIRSPY_SPEED
from authlib.integrations.flask_client import OAuth
from datetime import datetime

load_dotenv()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.logger.setLevel(logging.INFO)
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
        SECRET_KEY="MooCow2804",
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

    from Site.code.database.main import init_app
    init_app(app)

    def create_job(func):
        def wrapper():
            with app.app_context():
                func(app)
        return wrapper

    if click.get_current_context(silent=True) is None:
        scheduler = APScheduler()
        scheduler.init_app(app)
        scheduler.add_job(
            id="tick_airspy",
            func=create_job(tick_airspy),
            trigger='interval',
            minutes=AIRSPY_UPDATE_TIMEOUT / AIRSPY_SPEED,
        )
        scheduler.add_job(
            id="tick_airspy_icons",
            func=create_job(tick_airspy_icons),
            trigger='interval',
            minutes=60,
        )
        scheduler.add_job(
            id="tick_airspy_startup",
            func=create_job(tick_airspy),
            trigger="date",
        )
        scheduler.add_job(
            id="tick_airspy_icons_startup",
            func=create_job(tick_airspy_icons),
            trigger="date",
        )

        scheduler.start()

        @app.context_processor
        def inject_global():
            user = None
            if 'user' in session:
                user = session['user']
            return dict(user=user, year=datetime.now().year)

    return app

app = create_app()