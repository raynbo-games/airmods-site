from datetime import datetime
from flask import Blueprint, render_template, session
from Site.code.auth.main import get_user, login_required

bp = Blueprint('airmods', __name__, url_prefix='/airmods')

@bp.context_processor
def inject_airmods_global():
    return dict(title="Airmods")

@bp.route('/')
def root():
    return render_template('airmods/index.html')