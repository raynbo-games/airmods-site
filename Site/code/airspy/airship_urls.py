import os, io, requests

DOMAIN = "airship.gg"

# CDN Information
CDN_SUBDOMAIN = "cdn"
CDN_PROTOCALL = "https://"
CDN_DOMAIN = f"{CDN_PROTOCALL}{CDN_SUBDOMAIN}.{DOMAIN}"

# API Information
API_SUBDOMAIN = "api"
API_PROTOCALL = "https://"
API_DOMAIN = f"{API_PROTOCALL}{API_SUBDOMAIN}.{DOMAIN}"

# CDN URLs
IMAGE_URL = f"{CDN_DOMAIN}/images"

# API URLs
USER_URL = f"{API_DOMAIN}/game-coordinator/users"
GAME_URL = f"{API_DOMAIN}/content/games"

# Get URLs

def get_image_url(image_id):
    return f"{IMAGE_URL}/{image_id}"

def get_user_id_url(user_id):
    return f"{USER_URL}/uid/{user_id}"

def get_user_name_url(username):
    return f"{USER_URL}/user?username={username}"

def get_game_id_url(game_id, liveStats=False):
    if liveStats:
        return f"{GAME_URL}/game-id/{game_id}?liveStats=true"
    return f"{GAME_URL}/game-id/{game_id}"

def get_game_slug_url(game_slug, liveStats=False):
    if liveStats:
        return f"{GAME_URL}/slug/{game_slug}?liveStats=true"
    return f"{GAME_URL}/slug/{game_slug}"

# Get Headers

def get_headers():
    return {
        "Authorization": os.getenv("AIRSHIP_AUTHORIZATION"),
    }

# Request Utils

def request_url(url, func=None):
    res = requests.get(url, headers=get_headers())
    if res.status_code == 200:
        if func:
            return func(res)
        return res
    return None

def request_image_url(url):
    return request_url(url, func=lambda res: io.BytesIO(res.content))

def request_json_url(url):
    return request_url(url, func=lambda res: res.json())

# Requests

def request_image(image_id):
    return request_image_url(get_image_url(image_id))

def request_user_id(user_id):
    return request_json_url(get_user_id_url(user_id))

def request_user_name(username):
    return request_json_url(get_user_name_url(username))

def request_games():
    return request_json_url(GAME_URL)

def request_game_id(game_id, liveStats=False):
    return request_json_url(get_game_id_url(game_id, liveStats=liveStats))

def request_game_slug(game_slug, liveStats=False):
    return request_json_url(get_game_slug_url(game_slug, liveStats=liveStats))