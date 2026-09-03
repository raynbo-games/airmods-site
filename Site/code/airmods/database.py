import secrets, hashlib
from datetime import datetime, timezone
from Site.code.database.main import get_db, get_matching_row

TOKEN_PREFIX = "rgat_"

def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_api_token(game_id, user_id, name):
    token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "game_api_token" ("gameId", "userId", "name", "tokenHash", "createdAt") VALUES (%s, %s, %s, %s, %s)',
        (game_id, user_id, name, hash_token(token), datetime.now(timezone.utc).replace(tzinfo=None))
    )
    db.commit()
    return token

def get_api_tokens_for_game(game_id):
    return get_matching_row("game_api_token", {"gameId": game_id}, multiple=True)

def revoke_api_token(token_id, game_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'DELETE FROM "game_api_token" WHERE "id" = %s AND "gameId" = %s',
        (token_id, game_id)
    )
    db.commit()
