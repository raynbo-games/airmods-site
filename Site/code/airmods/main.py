from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from Site.code.airspy.api import bp as api_bp, get_image, get_search_items, get_dashboard_data
from Site.code.airspy.database import get_matching_row

bp = Blueprint('airmods', __name__, url_prefix='/airmods')