from datetime import datetime
from flask import render_template
from werkzeug.exceptions import HTTPException
from Site.code.auth.main import get_user
from Site.code.database.cdn import cdn, cdn_script, cdn_style, cdn_image

def init_context(app):
    @app.context_processor
    def inject_global():
        user = get_user()
        return dict(user=user, year=datetime.now().year, cdn=cdn, cdn_script=cdn_script, cdn_style=cdn_style, cdn_image=cdn_image)

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            error_code = e.code
            error_message = e.description
        else:
            error_code = 500
            error_message = "Internal Server Error"
        
        return render_template('error.html', error_code=error_code, error_message=error_message), error_code

