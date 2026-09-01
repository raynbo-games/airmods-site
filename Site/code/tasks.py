from flask_apscheduler import APScheduler
import click
from Site.code.airspy.processes import tick_airspy, tick_airspy_icons
from Site.code.config import AIRSPY_UPDATE_TIMEOUT, AIRSPY_SPEED


def init_tasks(app):
    if click.get_current_context(silent=True):
        return

    def create_job(func):
        def wrapper():
            with app.app_context():
                func(app)
        return wrapper

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