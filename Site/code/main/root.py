from flask import Blueprint, redirect, render_template

bp = Blueprint('root', __name__, url_prefix='/')

@bp.route('')
@bp.route('/home')
def home():
    return render_template(
        'root/index.html',
        title="Home",
    )

@bp.route('/tos')
def tos():
    return redirect("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

@bp.route('/privacy')
def privacy():
    return render_template(
        'root/privacy.html',
        title="Privacy Policy",
    )