from datetime import datetime
from flask import Blueprint, render_template

bp = Blueprint('airmods', __name__, url_prefix='/airmods')

@bp.route('/')
def airmods():
    return render_template(
        'airmods/index.html',
        title="Airmods",
        year=datetime.now().year,
    )
