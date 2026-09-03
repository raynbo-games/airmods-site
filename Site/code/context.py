from datetime import datetime
from flask import render_template, current_app
from werkzeug.exceptions import HTTPException
from Site.code.auth.main import get_user
from Site.code.database.cdn import cdn, cdn_script, cdn_style, cdn_image
from Site.code.community.database import get_unread_notification_count

def init_context(app):
    @app.context_processor
    def inject_global():
        user = get_user()
        unread_notifications = get_unread_notification_count(user["id"]) if user else 0
        return dict(user=user, unread_notifications=unread_notifications, year=datetime.now().year, cdn=cdn, cdn_script=cdn_script, cdn_style=cdn_style, cdn_image=cdn_image)

    @app.errorhandler(Exception)
    def handle_exception(e):
        error_code = getattr(e, 'code', 500)
        error_message = getattr(e, 'description', 'An unknown error has occured')
        current_app.log_exception(e)
        
        return render_template('error.html', error_code=error_code, error_message=error_message), error_code

