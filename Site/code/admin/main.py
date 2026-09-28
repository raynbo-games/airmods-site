import uuid
from datetime import timezone
from flask import Blueprint, redirect, render_template, url_for, abort, request, jsonify
from Site.code.admin.database import AUDIT_ACTIONS, add_audit_log, get_audit_log
from Site.code.admin.digitalocean import (
    is_configured as do_is_configured, get_apps as do_get_apps, get_app_deployments as do_get_app_deployments,
    get_app_run_logs as do_get_app_run_logs, get_databases as do_get_databases, get_balance as do_get_balance,
    get_latest_invoice_items as do_get_latest_invoice_items, get_live_database_stats as do_get_live_database_stats
)
from Site.code.airspy.compile import compile_all_stats, recompile_after_visibility_change
from Site.code.airspy.database import get_all_games, get_airspy_settings, set_airspy_settings
from Site.code.auth.database import AUTH_LEVEL_VALUES, get_auth, update_auth, update_username, update_user_notes, verify_username
from Site.code.auth.main import auth_required, get_user
from Site.code.community.webhook import get_community_config, set_community_config, get_notification_events, NOTIFICATION_GROUPS, send_test_notifications
from Site.code.database.cdn import get_image_cdn_url
from Site.code.database.main import get_matching_row, get_multiple_property_values
from Site.code.settings.database import set_game_hidden

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

@bp.route('/airspy/games')
@auth_required("MODERATOR")
def airspy_games():
    games = [{
        "id": g["id"],
        "name": g["name"],
        "organizationName": g["organizationName"],
        "image_url": get_image_cdn_url("airspy", g["iconImageId"]),
        "lastVersionUpdate": g["lastVersionUpdate"],
        "hidden": g["hiddenFromAirspy"],
    } for g in get_all_games()]
    site_updated_after = get_airspy_settings().get("gamesUpdatedAfter") or ""
    return render_template('admin/airspy/games.html', games=games, site_updated_after=site_updated_after)

@bp.route('/airspy/settings/updated-after', methods=['POST'])
@auth_required("ADMIN")
def set_airspy_updated_after():
    reason = request.form.get("reason", "").strip()
    if not reason:
        abort(400, "A reason is required for this action")

    updated_after = request.form.get("updated_after", "").strip()
    settings = get_airspy_settings()
    settings["gamesUpdatedAfter"] = updated_after or None
    set_airspy_settings(settings)
    compile_all_stats(keep_ath=False)
    add_audit_log(
        get_user(), None, "set_airspy_updated_after_cutoff", reason,
        details=f"Set public Airspy 'updated after' cutoff to {updated_after or 'none (show all games)'}",
        extra_fields=[("Cutoff", updated_after or "None (show all games)")]
    )
    return redirect(url_for("admin.airspy_games"))

@bp.route('/airspy/games/<game_id>/hide', methods=['POST'])
@auth_required("ADMIN")
def set_airspy_game_hidden(game_id):
    game = get_matching_row("game", {"id": game_id})
    if not game:
        abort(404)

    reason = request.form.get("reason", "").strip()
    if not reason:
        abort(400, "A reason is required for this action")

    hidden = request.form.get("hidden") == "1"
    set_game_hidden(game_id, game["organizationId"], hidden)
    recompile_after_visibility_change(game["organizationId"])
    organization = get_matching_row("organization", {"id": game["organizationId"]})
    add_audit_log(
        get_user(), None, "hide_airspy_game" if hidden else "unhide_airspy_game", reason,
        details=f"{'Hid' if hidden else 'Unhid'} game {game['name']} ({game_id}) from Airspy",
        thumbnail_url=get_image_cdn_url("airspy", game["iconImageId"]),
        extra_fields=[
            ("Game", game["name"]),
            ("Organization", organization["name"] if organization else game["organizationId"]),
        ]
    )
    return redirect(url_for("admin.airspy_games", updated_after=request.form.get("updated_after", "")))

@bp.route('/airspy/recompile-stats', methods=['POST'])
@auth_required("ADMIN")
def recompile_airspy_stats():
    reason = request.form.get("reason", "").strip()
    if not reason:
        abort(400, "A reason is required for this action")

    organization_count = compile_all_stats(keep_ath=False)
    add_audit_log(
        get_user(), None, "recompile_airspy_stats", reason,
        details=f"Recompiled stats for {organization_count} organizations and the global stats from raw game data"
    )
    return redirect(url_for("admin.airspy_games"))

@bp.route('/community-settings', methods=['GET', 'POST'])
@auth_required("DEVELOPER")
def community_settings():
    config = get_community_config()
    events = get_notification_events()

    if request.method == 'POST':
        webhooks = []
        for webhook in config["webhooks"]:
            wid = webhook["id"]
            if request.form.get(f"webhook_delete_{wid}") == "on":
                continue
            webhooks.append({
                "id": wid,
                "name": request.form.get(f"webhook_name_{wid}", "").strip() or webhook["name"],
                "url": request.form.get(f"webhook_url_{wid}", "").strip(),
            })

        new_name = request.form.get("new_webhook_name", "").strip()
        new_url = request.form.get("new_webhook_url", "").strip()
        if new_name and new_url:
            webhooks.append({"id": str(uuid.uuid4()), "name": new_name, "url": new_url})

        valid_webhook_ids = {webhook["id"] for webhook in webhooks}

        notifications = {}
        for event_key in events:
            webhook_id = request.form.get(f"notify_webhook_{event_key}", "").strip()
            if webhook_id not in valid_webhook_ids:
                webhook_id = None
            enabled = request.form.get(f"notify_enabled_{event_key}") == "on" and webhook_id is not None
            notifications[event_key] = {"enabled": enabled, "webhookId": webhook_id}

        set_community_config({
            "webhooks": webhooks,
            "notifications": notifications,
            "automodEnabled": request.form.get("automodEnabled") == "on",
            "automodWords": [w.strip() for w in request.form.get("automodWords", "").splitlines() if w.strip()],
        })
        return redirect(url_for("admin.community_settings"))

    grouped_keys = {key for _, keys in NOTIFICATION_GROUPS for key in keys}
    notification_groups = [(label, [(key, events[key]) for key in keys if key in events]) for label, keys in NOTIFICATION_GROUPS]
    other_events = [(key, label) for key, label in events.items() if key not in grouped_keys]
    if other_events:
        notification_groups.append(("Other", other_events))

    return render_template(
        'admin/community_settings.html', config=config, notification_groups=notification_groups,
        tested_count=request.args.get("tested", type=int), tested_name=request.args.get("tested_name")
    )

@bp.route('/community-settings/test/<webhook_id>', methods=['POST'])
@auth_required("DEVELOPER")
def test_webhook(webhook_id):
    config = get_community_config()
    webhook = next((w for w in config["webhooks"] if w["id"] == webhook_id), None)
    if not webhook or not webhook.get("url"):
        abort(404)

    sent = send_test_notifications(webhook["url"])
    return redirect(url_for("admin.community_settings", tested=sent, tested_name=webhook["name"]))

@bp.route('/infrastructure')
@auth_required("DEVELOPER")
def infrastructure():
    if not do_is_configured():
        return render_template('admin/infrastructure.html', configured=False)

    apps = do_get_apps()
    for app in apps:
        app["_deployments"] = do_get_app_deployments(app["id"], limit=5)

    latest_invoice, invoice_items = do_get_latest_invoice_items()

    return render_template(
        'admin/infrastructure.html', configured=True,
        apps=apps,
        databases=do_get_databases(),
        balance=do_get_balance(),
        live_db_stats=do_get_live_database_stats(),
        latest_invoice=latest_invoice,
        invoice_items=invoice_items,
    )

@bp.route('/infrastructure/apps/<app_id>/logs')
@auth_required("DEVELOPER")
def infrastructure_app_logs(app_id):
    component_name = request.args.get("component_name") or None
    logs = do_get_app_run_logs(app_id, component_name=component_name)
    return jsonify({"logs": logs or "No logs available right now - the app may not have an active deployment, or logs may still be spinning up."})
