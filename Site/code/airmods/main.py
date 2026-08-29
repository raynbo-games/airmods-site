from flask import Blueprint, render_template

bp = Blueprint('airmods', __name__, url_prefix='/airmods')

@bp.context_processor
def inject_airmods_global():
    return dict(title="Airmods")

@bp.route('/')
def root():
    return render_template('airmods/index.html')