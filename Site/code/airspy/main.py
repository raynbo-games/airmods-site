from datetime import datetime
from flask import Blueprint, render_template

from Site.code.airspy.airship_urls import get_image_url, get_headers

from Site.code.airspy.api import bp as api_bp

bp = Blueprint('airspy', __name__, url_prefix='/airspy')

@bp.route('/')
def airspy():
    return render_template(
        'airspy/index.html',
        title="Airspy",
        year=datetime.now().year,
    )

bp.register_blueprint(api_bp)