import re
from datetime import datetime, timezone
from Site.code.database.main import get_db, get_matching_row

STATUSES = ["planned", "in_progress", "completed", "canceled"]

def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def slugify(name):
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug or "roadmap"

def create_roadmap(name):
    """Create a roadmap, appending a numeric suffix to the slug if it already exists."""
    db = get_db()
    cursor = db.cursor()

    base_slug = slugify(name)
    slug = base_slug
    suffix = 2
    while get_matching_row("roadmap", {"slug": slug}):
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    now = now_utc()
    cursor.execute(
        'INSERT INTO "roadmap" ("name", "slug", "createdAt", "updatedAt") VALUES (%s, %s, %s, %s) RETURNING "id"',
        (name, slug, now, now)
    )
    roadmap_id = cursor.fetchone()["id"]
    db.commit()
    return roadmap_id, slug

def get_roadmaps():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM "roadmap" ORDER BY "name" ASC')
    return cursor.fetchall()

def get_roadmap(slug):
    return get_matching_row("roadmap", {"slug": slug})

def touch_roadmap(roadmap_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE "roadmap" SET "updatedAt" = %s WHERE "id" = %s', (now_utc(), roadmap_id))
    db.commit()

def rename_roadmap(roadmap_id, name):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE "roadmap" SET "name" = %s, "updatedAt" = %s WHERE "id" = %s', (name, now_utc(), roadmap_id))
    db.commit()

def delete_roadmap(roadmap_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM "roadmap_arrow" WHERE "roadmapId" = %s', (roadmap_id,))
    cursor.execute('DELETE FROM "roadmap_box" WHERE "roadmapId" = %s', (roadmap_id,))
    cursor.execute('DELETE FROM "roadmap" WHERE "id" = %s', (roadmap_id,))
    db.commit()

def get_boxes(roadmap_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM "roadmap_box" WHERE "roadmapId" = %s ORDER BY "id" ASC', (roadmap_id,))
    return cursor.fetchall()

def get_box(box_id):
    return get_matching_row("roadmap_box", {"id": box_id})

def create_box(roadmap_id, title, description, status, x, y):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "roadmap_box" ("roadmapId", "title", "description", "status", "x", "y") VALUES (%s, %s, %s, %s, %s, %s) RETURNING "id"',
        (roadmap_id, title, description, status, x, y)
    )
    box_id = cursor.fetchone()["id"]
    db.commit()
    return box_id

def update_box(box_id, title, description, status):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "roadmap_box" SET "title" = %s, "description" = %s, "status" = %s WHERE "id" = %s',
        (title, description, status, box_id)
    )
    db.commit()

def update_box_position(box_id, x, y):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE "roadmap_box" SET "x" = %s, "y" = %s WHERE "id" = %s', (x, y, box_id))
    db.commit()

def delete_box(box_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM "roadmap_arrow" WHERE "fromBoxId" = %s OR "toBoxId" = %s', (box_id, box_id))
    cursor.execute('DELETE FROM "roadmap_box_vote" WHERE "boxId" = %s', (box_id,))
    cursor.execute('DELETE FROM "roadmap_comment_vote" WHERE "commentId" IN (SELECT "id" FROM "roadmap_box_comment" WHERE "boxId" = %s)', (box_id,))
    cursor.execute('DELETE FROM "roadmap_box_comment" WHERE "boxId" = %s', (box_id,))
    cursor.execute('DELETE FROM "roadmap_box" WHERE "id" = %s', (box_id,))
    db.commit()

def get_box_score(box_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COALESCE(SUM("value"), 0) AS "score" FROM "roadmap_box_vote" WHERE "boxId" = %s', (box_id,))
    return cursor.fetchone()["score"]

def get_user_box_vote(box_id, user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT "value" FROM "roadmap_box_vote" WHERE "boxId" = %s AND "userId" = %s', (box_id, user_id))
    row = cursor.fetchone()
    return row["value"] if row else 0

def cast_box_vote(box_id, user_id, value):
    """Toggle a user's vote off if it matches the existing value, otherwise set/replace it."""
    db = get_db()
    cursor = db.cursor()
    current = get_user_box_vote(box_id, user_id)
    if current == value:
        cursor.execute('DELETE FROM "roadmap_box_vote" WHERE "boxId" = %s AND "userId" = %s', (box_id, user_id))
    else:
        cursor.execute(
            'INSERT INTO "roadmap_box_vote" ("boxId", "userId", "value") VALUES (%s, %s, %s) '
            'ON CONFLICT ("boxId", "userId") DO UPDATE SET "value" = %s',
            (box_id, user_id, value, value)
        )
    db.commit()

def get_box_comments(box_id, include_deleted=False):
    db = get_db()
    cursor = db.cursor()
    if include_deleted:
        cursor.execute('SELECT * FROM "roadmap_box_comment" WHERE "boxId" = %s ORDER BY "createdAt" ASC', (box_id,))
    else:
        cursor.execute('SELECT * FROM "roadmap_box_comment" WHERE "boxId" = %s AND "deleted" = FALSE ORDER BY "createdAt" ASC', (box_id,))
    return cursor.fetchall()

def get_box_comment_count(box_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) AS "count" FROM "roadmap_box_comment" WHERE "boxId" = %s AND "deleted" = FALSE', (box_id,))
    return cursor.fetchone()["count"]

def get_box_comment(comment_id):
    return get_matching_row("roadmap_box_comment", {"id": comment_id})

def create_box_comment(box_id, author, body, parent_comment_id=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "roadmap_box_comment" ("boxId", "authorId", "authorUsername", "body", "parentCommentId", "createdAt") VALUES (%s, %s, %s, %s, %s, %s) RETURNING "id"',
        (box_id, author["id"], author["username"], body, parent_comment_id, now_utc())
    )
    comment_id = cursor.fetchone()["id"]
    db.commit()
    return comment_id

def delete_box_comment(comment_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE "roadmap_box_comment" SET "deleted" = TRUE WHERE "id" = %s', (comment_id,))
    db.commit()

def get_comment_score(comment_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) AS "count" FROM "roadmap_comment_vote" WHERE "commentId" = %s', (comment_id,))
    return cursor.fetchone()["count"]

def has_user_upvoted_comment(comment_id, user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT 1 FROM "roadmap_comment_vote" WHERE "commentId" = %s AND "userId" = %s', (comment_id, user_id))
    return cursor.fetchone() is not None

def toggle_comment_upvote(comment_id, user_id):
    db = get_db()
    cursor = db.cursor()
    if has_user_upvoted_comment(comment_id, user_id):
        cursor.execute('DELETE FROM "roadmap_comment_vote" WHERE "commentId" = %s AND "userId" = %s', (comment_id, user_id))
        db.commit()
        return False
    cursor.execute('INSERT INTO "roadmap_comment_vote" ("commentId", "userId") VALUES (%s, %s)', (comment_id, user_id))
    db.commit()
    return True

def get_arrows(roadmap_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM "roadmap_arrow" WHERE "roadmapId" = %s', (roadmap_id,))
    return cursor.fetchall()

def get_arrow(arrow_id):
    return get_matching_row("roadmap_arrow", {"id": arrow_id})

def create_arrow(roadmap_id, from_box_id, to_box_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "roadmap_arrow" ("roadmapId", "fromBoxId", "toBoxId") VALUES (%s, %s, %s) RETURNING "id"',
        (roadmap_id, from_box_id, to_box_id)
    )
    arrow_id = cursor.fetchone()["id"]
    db.commit()
    return arrow_id

def delete_arrow(arrow_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM "roadmap_arrow" WHERE "id" = %s', (arrow_id,))
    db.commit()
