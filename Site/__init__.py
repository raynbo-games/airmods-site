import os, logging, click
from flask import Flask
from flask_apscheduler import APScheduler
from Site.code.airspy.processes import tick_airspy
from Site.code.config import AIRSPY_UPDATE_TIMEOUT, AIRSPY_SPEED

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.logger.setLevel(logging.DEBUG)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        DATABASE_URL = os.environ.get('DATABASE_URL'),
    )

    os.makedirs(app.instance_path, exist_ok=True)

    import Site.code.main.root as root
    app.register_blueprint(root.bp)

    import Site.code.airspy.main as airspy
    app.register_blueprint(airspy.bp)

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
            id="tick_airspy_startup",
            func=create_job(tick_airspy),
            trigger="date",
        )

        scheduler.start()

    return app

app = create_app()