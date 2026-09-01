from datetime import timezone
from flask import Blueprint, redirect, render_template, url_for, abort, request
from Site.code.admin.database import AUDIT_ACTIONS, add_audit_log, get_audit_log
from Site.code.auth.database import AUTH_LEVEL_VALUES, get_auth, update_auth, update_username, update_user_notes, verify_username
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
    assignable_auth_levels = [(name, value) for name, value in AUTH_LEVEL_VALUES.items() if value < get_user()["auth"]]
    return render_template('admin/user/view.html', data=data, assignable_auth_levels=assignable_auth_levels)

@bp.route('/users/<user_id>/set-auth', methods=['POST'])
@auth_required("ADMIN")
def set_user_auth(user_id):
    data = get_matching_row("user", { "id": user_id })
    if data["auth"] >= get_user()["auth"]:
        abort(403, "Cannot modify a user of same or more privilege")

    new_level = request.form.get("auth")
    if new_level not in AUTH_LEVEL_VALUES or get_auth(new_level) >= get_user()["auth"]:
        abort(400, "Invalid auth level")

    reason = request.form.get("reason", "").strip()
    if not reason:
        abort(400, "A reason is required for this action")

    old_level = next(name for name, value in AUTH_LEVEL_VALUES.items() if value == data["auth"])
    update_auth(data["id"], new_level)
    add_audit_log(get_user(), data, "set_user_auth", reason, details=f"Auth level changed from {old_level} to {new_level}")
    return redirect(url_for("admin.user", user_id=user_id))

@bp.route('/users/<user_id>/notes', methods=['POST'])
@auth_required("ADMIN")
def set_user_notes(user_id):
    data = get_matching_row("user", { "id": user_id })
    if data["auth"] >= get_user()["auth"]:
        abort(403, "Cannot modify a user of same or more privilege")

    reason = request.form.get("reason", "").strip()
    if not reason:
        abort(400, "A reason is required for this action")

    notes = request.form.get("notes", "").strip()
    update_user_notes(data["id"], notes)
    add_audit_log(get_user(), data, "set_user_notes", reason, details="Notes updated")
    return redirect(url_for("admin.user", user_id=user_id))

@bp.route('/users/<user_id>/username', methods=['POST'])
@auth_required("ADMIN")
def set_user_username(user_id):
    data = get_matching_row("user", { "id": user_id })
    if data["auth"] >= get_user()["auth"]:
        abort(403, "Cannot modify a user of same or more privilege")

    reason = request.form.get("reason", "").strip()
    if not reason:
        abort(400, "A reason is required for this action")

    new_username = request.form.get("username", "").strip()
    if new_username and new_username != data["username"]:
        verify = verify_username(new_username)
        if not verify["valid"]:
            abort(400, verify["message"])
        old_username = data["username"]
        update_username(data["id"], new_username)
        add_audit_log(get_user(), data, "set_user_username", reason, details=f"Username changed from {old_username} to {new_username}")

    return redirect(url_for("admin.user", user_id=user_id))

@bp.route('/audit-log')
@auth_required("ADMIN")
def audit_log():
    filters = {
        "actor": request.args.get("actor", "").strip(),
        "action": request.args.get("action", "").strip(),
        "since": request.args.get("since", "").strip(),
        "until": request.args.get("until", "").strip(),
        "reason": request.args.get("reason", "").strip(),
    }

    entries = []
    for entry in get_audit_log(filters):
        entry = dict(entry)
        entry["createdAtIso"] = entry["createdAt"].replace(tzinfo=timezone.utc).isoformat()
        entries.append(entry)

    return render_template('admin/audit_log.html', entries=entries, filters=filters, actions=AUDIT_ACTIONS)
