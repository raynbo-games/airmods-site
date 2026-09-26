from flask_apscheduler import APScheduler
from datetime import datetime
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
    # A single interval job per task, primed to fire immediately via next_run_time,
    # so each task runs once at startup and then on its normal interval - no second
    # "_startup" job racing the same DB row against the interval job.
    scheduler.add_job(
        id="tick_airspy",
        func=create_job(tick_airspy),
        trigger='interval',
        minutes=AIRSPY_UPDATE_TIMEOUT / AIRSPY_SPEED,
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        id="tick_airspy_icons",
        func=create_job(tick_airspy_icons),
        trigger='interval',
        minutes=60,
        next_run_time=datetime.now(),
    )

    scheduler.start()