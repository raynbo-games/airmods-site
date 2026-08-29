from flask import Blueprint, redirect, render_template, url_for, abort
from Site.code.auth.database import update_auth
from Site.code.auth.main import auth_required, get_user
from Site.code.database.main import get_matching_row, get_multiple_property_values

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.context_processor
def inject_auth_global():
    return dict(title="Admin")

@bp.route('')
@auth_required("MODERATOR")
def root():
    return render_template('admin/index.html')

@bp.route('/users')
@auth_required("MODERATOR")
def users():
    data = get_multiple_property_values("user", "id", "username")
    return render_template('admin/user/index.html', data=data)

@bp.route('/users/<user_id>')
@auth_required("MODERATOR")
def user(user_id):
    data = get_matching_row("user", { "id": user_id })
    return render_template('admin/user/view.html', data=data)

@bp.route('/users/<user_id>/ban')
@auth_required("ADMIN")
def ban_user(user_id):
    data = get_matching_row("user", { "id": user_id })
    if data["auth"] >= get_user()["auth"]:
        abort(403, "Cannot modify a user of same or more privilege")
    update_auth(data["id"], "BANNED")
    return redirect(url_for("admin.user", user_id=user_id))

@bp.route('/users/<user_id>/unban')
@auth_required("ADMIN")
def unban_user(user_id):
    data = get_matching_row("user", { "id": user_id })
    if data["auth"] != -1:
        abort(500, "Cannot unban a user who is not banned")
    update_auth(data["id"], "USER")
    return redirect(url_for("admin.user", user_id=user_id))