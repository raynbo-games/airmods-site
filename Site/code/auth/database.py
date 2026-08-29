from Site.code.database.main import get_db
from Site.code.airspy.database import get_matching_row

def create_user(userID, email, username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "user" ("id", "email", "username") VALUES (%s, %s, %s)',
        (userID, email, username)
    )
    db.commit()

def get_user_from_username(username):
    return get_matching_row("user", {"username": username})

def get_user_from_id(userID):
    return get_matching_row("user", {"id": userID})

def verify_username(username):
    if not username:
        return {
            "valid": False, 
            "message": "Username is null"
        }

    if not username.isalnum():
        return {
            "valid": False, 
            "message": "Username can only contain letters and numbers."
        }

    if len(username) < 3 or len(username) > 30:
        return {
            "valid": False, 
            "message": "Username must be between 3 and 30 characters."
        }

    if get_user_from_username(username): 
        return {
                    "valid": False, 
                    "message": "This username is already taken."
                }

    return {
            "valid": True, 
            "message": "Username is available!"
        }

def update_username(userID, username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "user" SET "username" = %s WHERE "id" = %s',
        (username, userID)
    )
    db.commit()