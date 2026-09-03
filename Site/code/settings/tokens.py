from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app
from Site.code.config import AIRSPY_ORG_LINK_TOKEN_MAX_AGE

SALT = "settings-org-link"

def get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT)

def create_link_token(user_id, organization_id, game_id):
    return get_serializer().dumps({
        "userId": user_id,
        "organizationId": organization_id,
        "gameId": game_id,
    })

def read_link_token(token):
    """Returns (payload, error) where error is None, "expired", or "invalid"."""
    try:
        return get_serializer().loads(token, max_age=AIRSPY_ORG_LINK_TOKEN_MAX_AGE), None
    except SignatureExpired:
        return None, "expired"
    except BadSignature:
        return None, "invalid"
