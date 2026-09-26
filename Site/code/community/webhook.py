import time
import uuid
import requests
from psycopg.types.json import Jsonb
from Site.code.database.main import get_db, get_matching_row
from Site.code.database.cdn import get_image_cdn_url

# Audit-logged actions whose real add_audit_log() call passes a target user
# (the account being changed, or a suggestion/comment's author) - used so
# test previews include a sample Target field exactly where the real
# notification would have one.
_AUDIT_ACTIONS_WITH_TARGET = {
    "set_user_auth", "set_user_notes", "set_user_username",
    "hide_suggestion", "unhide_suggestion", "edit_suggestion", "delete_suggestion",
    "approve_suggestion", "reject_suggestion",
    "hide_comment", "unhide_comment", "edit_comment", "delete_comment",
    "approve_comment", "reject_comment",
}

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

DISCORD_EMBED_COLOR = 0x5BC0DE  # matches the site's accent color

def build_embed(title, description=None, fields=None, thumbnail_url=None, color=DISCORD_EMBED_COLOR):
    """Build a Discord embed dict. fields is a list of (name, value) or
    (name, value, inline) tuples; inline defaults to True."""
    embed = {"title": title[:256], "color": color}
    if description:
        embed["description"] = description[:4096]
    if fields:
        embed["fields"] = [{
            "name": str(field[0])[:256],
            "value": str(field[1])[:1024],
            "inline": field[2] if len(field) > 2 else True,
        } for field in fields if field[1]]
    if thumbnail_url:
        embed["thumbnail"] = {"url": thumbnail_url}
    return embed

def send_discord_notification(event_key, message=None, embed=None):
    config = get_community_config()
    setting = config["notifications"].get(event_key)
    if not setting or not setting.get("enabled"):
        return

    webhook = next((w for w in config["webhooks"] if w["id"] == setting.get("webhookId")), None)
    if not webhook or not webhook.get("url"):
        return

    payload = {}
    if message:
        payload["content"] = message[:2000]
    if embed:
        payload["embeds"] = [embed]
    if not payload:
        return

    try:
        requests.post(webhook["url"], json=payload, timeout=5)
    except requests.RequestException:
        pass

def _sample_game():
    """A random real tracked game (name, icon URL, organization name), or
    made-up placeholder data if none are tracked yet."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM "game" ORDER BY random() LIMIT 1')
    row = cursor.fetchone()
    if row:
        organization = get_matching_row("organization", {"id": row["organizationId"]})
        icon_url = get_image_cdn_url("airspy", row["iconImageId"]) if row["iconImageId"] else None
        return row["name"], icon_url, organization["name"] if organization else "Sample Organization"
    return "Catch a Fish!", None, "Sample Organization"

def _sample_organization():
    """A random real tracked organization (name, icon URL), or made-up
    placeholder data if none are tracked yet."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM "organization" ORDER BY random() LIMIT 1')
    row = cursor.fetchone()
    if row:
        icon_url = get_image_cdn_url("airspy", row["iconImageId"]) if row["iconImageId"] else None
        return row["name"], icon_url
    return "Sample Organization", None

def build_preview_embed(event_key):
    """Build the embed for event_key in exactly the format the real
    notification would use, populated with a random real game/org from the
    database (or made-up data if none exist yet). Used by the notification
    settings page's per-webhook "Test" button."""
    from Site.code.admin.database import AUDIT_ACTIONS, build_audit_embed

    if event_key in AUDIT_ACTIONS:
        target_username = "SampleUser" if event_key in _AUDIT_ACTIONS_WITH_TARGET else None
        thumbnail_url = None
        extra_fields = None

        if event_key in ("link_organization", "unlink_organization"):
            org_name, org_icon = _sample_organization()
            thumbnail_url = org_icon
            extra_fields = [("Organization", org_name)]
        elif event_key in ("link_game", "hide_airspy_game", "unhide_airspy_game"):
            game_name, game_icon, game_org_name = _sample_game()
            thumbnail_url = game_icon
            extra_fields = [("Game", game_name), ("Organization", game_org_name)]
        elif event_key == "set_airspy_updated_after_cutoff":
            extra_fields = [("Cutoff", "2026-01-01")]

        return build_audit_embed(
            "SampleAdmin", event_key, "This is a sample reason for testing.",
            target_username=target_username, details="Sample details for this action.",
            thumbnail_url=thumbnail_url, extra_fields=extra_fields
        )

    if event_key == "airspy_game_created":
        game_name, game_icon, game_org_name = _sample_game()
        return build_embed("\U0001F195 New Airspy Game Tracked", fields=[("Game", game_name), ("Organization", game_org_name)], thumbnail_url=game_icon)

    if event_key == "airspy_game_version_updated":
        game_name, game_icon, game_org_name = _sample_game()
        return build_embed("\U0001F504 Airspy Game Updated", fields=[("Game", game_name), ("Organization", game_org_name)], thumbnail_url=game_icon)

    if event_key == "airspy_organization_created":
        org_name, org_icon = _sample_organization()
        return build_embed("\U0001F195 New Airspy Organization Tracked", fields=[("Organization", org_name)], thumbnail_url=org_icon)

    if event_key == "new_post":
        return build_embed("\U0001F4A1 New Suggestion Posted", fields=[("Author", "SampleUser"), ("Title", "Sample Suggestion Title", False)])

    if event_key == "edited_post":
        return build_embed("✏️ Suggestion Edited", fields=[("Moderator", "SampleAdmin"), ("Title", "Sample Suggestion Title", False)])

    if event_key == "comment":
        return build_embed("\U0001F4AC New Comment", fields=[("Author", "SampleUser"), ("On", "Sample Suggestion Title")])

    if event_key == "roadmap_new_step":
        return build_embed("\U0001F5FA️ New Roadmap Step", fields=[("User", "SampleAdmin"), ("Roadmap", "Sample Roadmap"), ("Step", "Sample Step Title", False)])

    if event_key == "roadmap_edited_step":
        return build_embed("✏️ Roadmap Step Edited", fields=[("User", "SampleAdmin"), ("Roadmap", "Sample Roadmap"), ("Step", "Sample Step Title", False)])

    if event_key == "roadmap_comment":
        return build_embed("\U0001F4AC Roadmap Comment", fields=[("Author", "SampleUser"), ("Roadmap", "Sample Roadmap"), ("Step", "Sample Step Title", False)])

    return build_embed(event_key, description="No preview available for this event.")

def send_test_notifications(webhook_url):
    """POST a realistic sample embed for every known notification event
    straight to webhook_url, ignoring each event's configured
    enabled/webhookId - used by the admin settings page's "Test" button to
    preview real formatting for a single webhook without waiting for each
    real event to fire."""
    sent = 0
    for event_key in get_notification_events():
        embed = build_preview_embed(event_key)
        try:
            requests.post(webhook_url, json={"embeds": [embed]}, timeout=5)
            sent += 1
        except requests.RequestException:
            pass
        time.sleep(0.4)
    return sent

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
