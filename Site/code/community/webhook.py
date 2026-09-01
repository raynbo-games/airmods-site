import requests
from psycopg.types.json import Jsonb
from Site.code.database.main import get_db, get_matching_row

CONFIG_ID = "community_config"

default_config = {
    "discordWebhookUrl": "",
    "notifyAuditLog": False,
    "notifyNewPost": False,
    "notifyEditedPost": False,
    "notifyComment": False,
    "notifyRoadmapNewStep": False,
    "notifyRoadmapEditedStep": False,
    "notifyRoadmapComment": False,
    "automodEnabled": True,
    "automodWords": [],
}

def get_community_config():
    row = get_matching_row("json", {"id": CONFIG_ID})
    if row:
        return {**default_config, **row["data"]}

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "json" ("id", "data") VALUES (%s, %s)',
        (CONFIG_ID, Jsonb(default_config))
    )
    db.commit()
    return dict(default_config)

def set_community_config(config):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "json" SET "data" = %s WHERE "id" = %s',
        (Jsonb(config), CONFIG_ID)
    )
    db.commit()

def send_discord_notification(event_key, message):
    config = get_community_config()
    webhook_url = config.get("discordWebhookUrl")
    if not webhook_url:
        return
    if not config.get(f"notify{event_key}", False):
        return

    try:
        requests.post(webhook_url, json={"content": message[:2000]}, timeout=5)
    except requests.RequestException:
        pass

def check_automod(text):
    config = get_community_config()
    if not config.get("automodEnabled", True):
        return False

    lowered = text.lower()
    for word in config.get("automodWords", []):
        word = word.strip().lower()
        if word and word in lowered:
            return True
    return False
