"""
Routes and views for the flask application.
"""

from flask import Blueprint, redirect, render_template
from datetime import datetime

bp = Blueprint('root', __name__, url_prefix='/')

@bp.route('/')
@bp.route('/home')
def home():
    """Renders the home page."""
    return render_template(
        'root/index.html',
        title="Home",
        year=datetime.now().year,
    )

@bp.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template(
        'root/contact.html',
        title="Contact",
        year=datetime.now().year,
    )

@bp.route('/about')
def about():
    """Renders the about page."""
    return render_template(
        'root/about.html',
        title="About",
        year=datetime.now().year,
    )

@bp.route('/tos')
def tos():
    """Renders the tos page."""
    return redirect("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


@bp.route('/privacy')
def privacy():
    """Renders the privacy policy."""
    return render_template(
        'root/privacy.html',
        title="Privacy Policy",
        year=datetime.now().year,
    )
