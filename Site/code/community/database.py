from datetime import datetime, timezone
from Site.code.database.main import get_db, get_matching_row
from Site.code.community.webhook import check_automod, send_discord_notification

def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# --- Suggestions ---

def create_suggestion(author, title, body):
    db = get_db()
    cursor = db.cursor()
    status = "pending_review" if check_automod(f"{title}\n{body}") else "visible"
    cursor.execute(
        'INSERT INTO "suggestion" ("authorId", "authorUsername", "title", "body", "status", "createdAt") VALUES (%s, %s, %s, %s, %s, %s) RETURNING "id"',
        (author["id"], author["username"], title, body, status, now_utc())
    )
    suggestion_id = cursor.fetchone()["id"]
    db.commit()

    if status == "visible":
        send_discord_notification("NewPost", f"\U0001F4A1 **{author['username']}** posted a new suggestion: *{title}*")

    return suggestion_id, status

def get_suggestion(suggestion_id):
    return get_matching_row("suggestion", {"id": suggestion_id})

def get_suggestions(status="visible", limit=100):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT * FROM "suggestion" WHERE "status" = %s ORDER BY "createdAt" DESC LIMIT %s',
        (status, limit)
    )
    return cursor.fetchall()

def get_pending_suggestions():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM "suggestion" WHERE "status" = %s ORDER BY "createdAt" ASC', ("pending_review",))
    return cursor.fetchall()

def update_suggestion(suggestion_id, title, body):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "suggestion" SET "title" = %s, "body" = %s, "editedAt" = %s WHERE "id" = %s',
        (title, body, now_utc(), suggestion_id)
    )
    db.commit()

def set_suggestion_status(suggestion_id, status):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE "suggestion" SET "status" = %s WHERE "id" = %s', (status, suggestion_id))
    db.commit()

def delete_suggestion(suggestion_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM "comment" WHERE "suggestionId" = %s', (suggestion_id,))
    cursor.execute('DELETE FROM "suggestion_vote" WHERE "suggestionId" = %s', (suggestion_id,))
    cursor.execute('DELETE FROM "suggestion" WHERE "id" = %s', (suggestion_id,))
    db.commit()

# --- Voting ---

def get_suggestion_score(suggestion_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COALESCE(SUM("value"), 0) AS "score" FROM "suggestion_vote" WHERE "suggestionId" = %s', (suggestion_id,))
    return cursor.fetchone()["score"]

def get_user_vote(suggestion_id, user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT "value" FROM "suggestion_vote" WHERE "suggestionId" = %s AND "userId" = %s', (suggestion_id, user_id))
    row = cursor.fetchone()
    return row["value"] if row else 0

def cast_vote(suggestion_id, user_id, value):
    db = get_db()
    cursor = db.cursor()
    current = get_user_vote(suggestion_id, user_id)
    if current == value:
        cursor.execute('DELETE FROM "suggestion_vote" WHERE "suggestionId" = %s AND "userId" = %s', (suggestion_id, user_id))
    else:
        cursor.execute(
            'INSERT INTO "suggestion_vote" ("suggestionId", "userId", "value") VALUES (%s, %s, %s) '
            'ON CONFLICT ("suggestionId", "userId") DO UPDATE SET "value" = %s',
            (suggestion_id, user_id, value, value)
        )
    db.commit()

# --- Comments ---

def create_comment(author, suggestion, body, parent_comment=None):
    db = get_db()
    cursor = db.cursor()
    status = "pending_review" if check_automod(body) else "visible"
    parent_comment_id = parent_comment["id"] if parent_comment else None
    cursor.execute(
        'INSERT INTO "comment" ("suggestionId", "authorId", "authorUsername", "body", "status", "parentCommentId", "createdAt") VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING "id"',
        (suggestion["id"], author["id"], author["username"], body, status, parent_comment_id, now_utc())
    )
    comment_id = cursor.fetchone()["id"]
    db.commit()

    if status == "visible":
        send_discord_notification("Comment", f"\U0001F4AC **{author['username']}** commented on *{suggestion['title']}*")
        if parent_comment:
            if parent_comment["authorId"] != author["id"]:
                add_notification(
                    parent_comment["authorId"],
                    f'{author["username"]} replied to your comment on "{suggestion["title"]}"',
                    url=f"/community/suggestions/{suggestion['id']}"
                )
        elif suggestion["authorId"] != author["id"]:
            add_notification(
                suggestion["authorId"],
                f'{author["username"]} commented on your suggestion "{suggestion["title"]}"',
                url=f"/community/suggestions/{suggestion['id']}"
            )

    return comment_id, status

def get_comments(suggestion_id, include_hidden=False):
    db = get_db()
    cursor = db.cursor()
    if include_hidden:
        cursor.execute('SELECT * FROM "comment" WHERE "suggestionId" = %s ORDER BY "createdAt" ASC', (suggestion_id,))
    else:
        cursor.execute('SELECT * FROM "comment" WHERE "suggestionId" = %s AND "status" = %s ORDER BY "createdAt" ASC', (suggestion_id, "visible"))
    return cursor.fetchall()

def get_comment(comment_id):
    return get_matching_row("comment", {"id": comment_id})

def get_pending_comments():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM "comment" WHERE "status" = %s ORDER BY "createdAt" ASC', ("pending_review",))
    return cursor.fetchall()

def update_comment(comment_id, body):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE "comment" SET "body" = %s, "editedAt" = %s WHERE "id" = %s', (body, now_utc(), comment_id))
    db.commit()

def set_comment_status(comment_id, status):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE "comment" SET "status" = %s WHERE "id" = %s', (status, comment_id))
    db.commit()

# --- Notifications ---

def add_notification(user_id, message, url=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "notification" ("userId", "message", "url", "createdAt") VALUES (%s, %s, %s, %s)',
        (user_id, message, url, now_utc())
    )
    db.commit()

def get_notifications(user_id, limit=50):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM "notification" WHERE "userId" = %s ORDER BY "createdAt" DESC LIMIT %s', (user_id, limit))
    return cursor.fetchall()

def get_unread_notification_count(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) AS "count" FROM "notification" WHERE "userId" = %s AND "read" = FALSE', (user_id,))
    return cursor.fetchone()["count"]

def mark_notifications_read(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE "notification" SET "read" = TRUE WHERE "userId" = %s AND "read" = FALSE', (user_id,))
    db.commit()
