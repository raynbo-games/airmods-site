from datetime import datetime, timezone
from Site.code.database.main import get_db
from Site.code.community.webhook import send_discord_notification, build_embed

AUDIT_ACTIONS = {
    "set_user_auth": "Changed Auth Level",
    "set_user_notes": "Updated Notes",
    "set_user_username": "Renamed User",
    "hide_suggestion": "Hid Suggestion",
    "unhide_suggestion": "Unhid Suggestion",
    "edit_suggestion": "Edited Suggestion",
    "delete_suggestion": "Deleted Suggestion",
    "approve_suggestion": "Approved Suggestion",
    "reject_suggestion": "Rejected Suggestion",
    "hide_comment": "Hid Comment",
    "unhide_comment": "Unhid Comment",
    "edit_comment": "Edited Comment",
    "delete_comment": "Deleted Comment",
    "approve_comment": "Approved Comment",
    "reject_comment": "Rejected Comment",
    "link_organization": "Linked Airship Organization",
    "unlink_organization": "Unlinked Airship Organization",
    "link_game": "Linked Airship Game",
    "create_api_token": "Created Airmods API Token",
    "revoke_api_token": "Revoked Airmods API Token",
    "hide_airspy_game": "Hid Airspy Game",
    "unhide_airspy_game": "Unhid Airspy Game",
    "set_airspy_updated_after_cutoff": "Set Airspy Updated-After Cutoff",
    "recompile_airspy_stats": "Recompiled Airspy Stats",
}

def build_audit_embed(actor_username, action, reason, target_username=None, details=None, thumbnail_url=None, extra_fields=None):
    """Build the embed for an audit-logged action. Shared by add_audit_log
    (real data) and the notification settings page's per-webhook test
    messages (sample data), so a preview always matches the real format."""
    action_label = AUDIT_ACTIONS.get(action, action)
    fields = [("Actor", actor_username)]
    if target_username:
        fields.append(("Target", target_username))
    if extra_fields:
        fields.extend(extra_fields)
    fields.append(("Reason", reason, False))
    if details:
        fields.append(("Details", details, False))
    return build_embed(f"\U0001F6E0️ {action_label}", fields=fields, thumbnail_url=thumbnail_url)

def add_audit_log(actor, target, action, reason, details=None, thumbnail_url=None, extra_fields=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "audit_log" ("actorId", "actorUsername", "action", "targetId", "targetUsername", "details", "reason", "createdAt") VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (actor["id"], actor["username"], action, target["id"] if target else None, target["username"] if target else None, details, reason, datetime.now(timezone.utc).replace(tzinfo=None))
    )
    db.commit()

    embed = build_audit_embed(
        actor["username"], action, reason,
        target_username=(target.get("username") or target.get("name")) if target else None,
        details=details, thumbnail_url=thumbnail_url, extra_fields=extra_fields
    )
    send_discord_notification(action, embed=embed)

def get_audit_log(filters=None, limit=200):
    filters = filters or {}
    db = get_db()
    cursor = db.cursor()

    conditions = []
    params = []

    if filters.get("actor"):
        conditions.append('"actorUsername" ILIKE %s')
        params.append(f'%{filters["actor"]}%')
    if filters.get("action"):
        conditions.append('"action" = %s')
        params.append(filters["action"])
    if filters.get("reason"):
        conditions.append('"reason" ILIKE %s')
        params.append(f'%{filters["reason"]}%')
    if filters.get("since"):
        conditions.append('"createdAt" >= %s')
        params.append(filters["since"])
    if filters.get("until"):
        conditions.append('"createdAt" <= %s')
        params.append(f'{filters["until"]} 23:59:59.999999')

    where_clause = f'WHERE {" AND ".join(conditions)}' if conditions else ''
    query = f'SELECT * FROM "audit_log" {where_clause} ORDER BY "createdAt" DESC LIMIT %s'
    params.append(limit)

    return cursor.execute(query, params).fetchall()
