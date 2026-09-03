from datetime import datetime, timezone
from Site.code.database.main import get_db
from Site.code.community.webhook import send_discord_notification

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
}

def add_audit_log(actor, target, action, reason, details=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "audit_log" ("actorId", "actorUsername", "action", "targetId", "targetUsername", "details", "reason", "createdAt") VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (actor["id"], actor["username"], action, target["id"] if target else None, target["username"] if target else None, details, reason, datetime.now(timezone.utc).replace(tzinfo=None))
    )
    db.commit()

    action_label = AUDIT_ACTIONS.get(action, action)
    target_note = f" on {target['username']}" if target else ""
    send_discord_notification("AuditLog", f"🛠️ **{actor['username']}** {action_label}{target_note} — _{reason}_")

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
