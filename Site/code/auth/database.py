from typing import Literal
from Site.code.database.main import get_db, get_matching_row

AUTH_LEVEL_VALUES = {
    "BANNED": -1,
    "USER": 0,
    "MODERATOR": 1,
    "ADMIN": 2,
    "DEVELOPER": 3,
    "OWNER": 4,
    "SYSTEM": 5,
}

AUTH_LEVEL = Literal["BANNED", "USER", "MODERATOR", "ADMIN", "DEVELOPER", "OWNER", "SYSTEM"]

def get_auth(level: AUTH_LEVEL):
    return AUTH_LEVEL_VALUES[level]

def create_user(user_id, email, username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "user" ("id", "email", "username") VALUES (%s, %s, %s)',
        (user_id, email, username)
    )
    db.commit()

def get_user_from_username(username):
    return get_matching_row("user", {"username": username})

def get_user_from_id(user_id):
    return get_matching_row("user", {"id": user_id})

def verify_username(username):
    if not username:
        return {"valid": False, "message": "Username is null"}

    if not username.isalnum():
        return {"valid": False, "message": "Username can only contain letters and numbers."}

    if len(username) < 3 or len(username) > 30:
        return {"valid": False, "message": "Username must be between 3 and 30 characters."}

    if get_user_from_username(username):
        return {"valid": False, "message": "This username is already taken."}

    return {"valid": True, "message": "Username is available!"}

def update_username(user_id, username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "user" SET "username" = %s WHERE "id" = %s',
        (username, user_id)
    )
    db.commit()

def update_auth(user_id, auth: AUTH_LEVEL):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "user" SET "auth" = %s WHERE "id" = %s',
        (get_auth(auth), user_id)
    )
    db.commit()

def update_user_notes(user_id, notes):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "user" SET "notes" = %s WHERE "id" = %s',
        (notes, user_id)
    )
    db.commit()
