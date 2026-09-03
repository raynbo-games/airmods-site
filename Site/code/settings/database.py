from datetime import datetime, timezone
from Site.code.database.main import get_db, get_matching_row
from Site.code.auth.database import verify_username

def get_linked_organizations(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT "organization".* FROM "organization_link" JOIN "organization" ON "organization_link"."organizationId" = "organization"."id" WHERE "organization_link"."userId" = %s ORDER BY "organization"."name"',
        (user_id,)
    )
    return cursor.fetchall()

def is_organization_linked_to_user(user_id, organization_id):
    return get_matching_row("organization_link", {"userId": user_id, "organizationId": organization_id}) is not None

def link_organization(user_id, organization_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "organization_link" ("userId", "organizationId", "linkedAt") VALUES (%s, %s, %s) ON CONFLICT ("userId", "organizationId") DO NOTHING',
        (user_id, organization_id, datetime.now(timezone.utc).replace(tzinfo=None))
    )
    db.commit()

def unlink_organization(user_id, organization_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'DELETE FROM "organization_link" WHERE "userId" = %s AND "organizationId" = %s',
        (user_id, organization_id)
    )
    db.commit()

def set_game_hidden(game_id, organization_id, hidden):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "game" SET "hiddenFromAirspy" = %s WHERE "id" = %s AND "organizationId" = %s',
        (hidden, game_id, organization_id)
    )
    db.commit()

def set_organization_hidden(organization_id, hidden):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "organization" SET "hiddenFromAirspy" = %s WHERE "id" = %s',
        (hidden, organization_id)
    )
    db.commit()

def get_games_for_user(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT "game".* FROM "organization_link" JOIN "game" ON "organization_link"."organizationId" = "game"."organizationId" WHERE "organization_link"."userId" = %s ORDER BY "game"."name"',
        (user_id,)
    )
    return cursor.fetchall()

def verify_username_change(user, username):
    if username == user["username"]:
        return {"valid": True, "message": "This is your current username."}
    return verify_username(username)
