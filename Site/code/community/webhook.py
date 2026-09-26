import uuid
import requests
from psycopg.types.json import Jsonb
from Site.code.database.main import get_db, get_matching_row

CONFIG_ID = "community_config"

# Notification events that aren't routed through the audit log: community
# content notifications, and system-level Airspy sync events with no acting
# user. Every audit-logged action (Site.code.admin.database.AUDIT_ACTIONS)
# gets its own notification toggle automatically alongside these, so an
# action doesn't need to be listed in two places.
EXTRA_NOTIFICATION_EVENTS = {
    "new_post": "New Suggestion Posted",
    "edited_post": "Suggestion Edited",
    "comment": "New Comment",
    "roadmap_new_step": "New Roadmap Step",
    "roadmap_edited_step": "Roadmap Step Edited",
    "roadmap_comment": "Roadmap Comment",
    "airspy_game_created": "New Airspy Game Tracked",
    "airspy_organization_created": "New Airspy Organization Tracked",
    "airspy_game_version_updated": "Airspy Game Updated (New Version)",
}

# How the notification settings UI groups event keys into sections. An event
# key not listed here still gets a toggle, just under an "Other" group.
NOTIFICATION_GROUPS = [
    ("Community", ["new_post", "edited_post", "comment", "roadmap_new_step", "roadmap_edited_step", "roadmap_comment"]),
    ("User Management", ["set_user_auth", "set_user_notes", "set_user_username"]),
    ("Suggestions", ["hide_suggestion", "unhide_suggestion", "edit_suggestion", "delete_suggestion", "approve_suggestion", "reject_suggestion"]),
    ("Comments", ["hide_comment", "unhide_comment", "edit_comment", "delete_comment", "approve_comment", "reject_comment"]),
    ("Airspy (Self-Service)", ["link_organization", "unlink_organization", "link_game"]),
    ("Airspy (Admin)", ["hide_airspy_game", "unhide_airspy_game", "set_airspy_updated_after_cutoff"]),
    ("Airspy (Sync)", ["airspy_game_created", "airspy_organization_created", "airspy_game_version_updated"]),
    ("Airmods", ["create_api_token", "revoke_api_token"]),
]

# event_key -> the old flat boolean flag it should carry its "enabled" value
# over from, the first time the new config shape is built for a site that
# already had settings saved under the old shape. Audit-logged actions have
# no individual match in the old shape - they all shared one catch-all flag.
LEGACY_NOTIFY_FLAGS = {
    "new_post": "notifyNewPost",
    "edited_post": "notifyEditedPost",
    "comment": "notifyComment",
    "roadmap_new_step": "notifyRoadmapNewStep",
    "roadmap_edited_step": "notifyRoadmapEditedStep",
    "roadmap_comment": "notifyRoadmapComment",
}

def get_notification_events():
    """Every event key the notification settings UI can toggle: every
    audit-logged action, plus the community/system events above."""
    from Site.code.admin.database import AUDIT_ACTIONS
    events = dict(AUDIT_ACTIONS)
    events.update(EXTRA_NOTIFICATION_EVENTS)
    return events

def _migrate_legacy_config(data):
    """Build the current webhooks list + per-event notification settings,
    carrying over the old single discordWebhookUrl + notify* flags the first
    time this runs for a site that had settings saved under the old shape."""
    webhooks = list(data.get("webhooks") or [])
    notifications = dict(data.get("notifications") or {})

    legacy_url = data.get("discordWebhookUrl")
    default_webhook_id = webhooks[0]["id"] if webhooks else None
    if not webhooks and legacy_url:
        default_webhook_id = str(uuid.uuid4())
        webhooks.append({"id": default_webhook_id, "name": "Admin Panel", "url": legacy_url})

    for event_key in get_notification_events():
        if event_key in notifications:
            continue
        legacy_flag = LEGACY_NOTIFY_FLAGS.get(event_key, "notifyAuditLog")
        enabled = bool(data.get(legacy_flag)) and default_webhook_id is not None
        notifications[event_key] = {"enabled": enabled, "webhookId": default_webhook_id if enabled else None}

    return webhooks, notifications

def get_community_config():
    row = get_matching_row("json", {"id": CONFIG_ID})
    data = row["data"] if row else {}

    webhooks, notifications = _migrate_legacy_config(data)
    config = {
        "webhooks": webhooks,
        "notifications": notifications,
        "automodEnabled": data.get("automodEnabled", True),
        "automodWords": data.get("automodWords", []),
    }

    if row is None:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO "json" ("id", "data") VALUES (%s, %s)',
            (CONFIG_ID, Jsonb(config))
        )
        db.commit()
    elif "webhooks" not in data:
        set_community_config(config)

    return config

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
    setting = config["notifications"].get(event_key)
    if not setting or not setting.get("enabled"):
        return

    webhook = next((w for w in config["webhooks"] if w["id"] == setting.get("webhookId")), None)
    if not webhook or not webhook.get("url"):
        return

    try:
        requests.post(webhook["url"], json={"content": message[:2000]}, timeout=5)
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
