from datetime import datetime, timezone
from Site.code.database.main import get_db

AUDIT_ACTIONS = {
    "set_user_auth": "Changed Auth Level",
    "set_user_notes": "Updated Notes",
    "set_user_username": "Renamed User",
}

def add_audit_log(actor, target, action, reason, details=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "audit_log" ("actorId", "actorUsername", "action", "targetId", "targetUsername", "details", "reason", "createdAt") VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (actor["id"], actor["username"], action, target["id"] if target else None, target["username"] if target else None, details, reason, datetime.now(timezone.utc).replace(tzinfo=None))
    )
    db.commit()

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
