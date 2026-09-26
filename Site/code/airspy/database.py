import click, time
from Site.code.database.main import get_db, get_matching_row
from Site.code.database.cdn import upload_to_spaces, get_image_cdn_url
from Site.code.airspy.airship_urls import get_image_url
from Site.code.community.webhook import send_discord_notification, build_embed
from Site.code.config import AIRSPY_SPEED, AIRSPY_UPDATE_TIMEOUT, STORED_TICKS, STORED_DAILY_TICKS, STORED_MONTHLY_TICKS
from psycopg.types.json import Jsonb
from datetime import datetime, timedelta, timezone

default_stats = {
    "playerCounts": [-1] * STORED_TICKS,
    "plays": [-1] * STORED_TICKS,
    "plays24h": [-1] * STORED_TICKS,
    "uniquePlays24h": [-1] * STORED_TICKS,
    "timestamps": [None] * STORED_TICKS,
    "dailyPlayerCounts": [-1] * STORED_DAILY_TICKS,
    "dailyPlays": [-1] * STORED_DAILY_TICKS,
    "dailyPlays24h": [-1] * STORED_DAILY_TICKS,
    "dailyUniquePlays24h": [-1] * STORED_DAILY_TICKS,
    "dailyTimestamps": [None] * STORED_DAILY_TICKS,
    "monthlyPlayerCounts": [-1] * STORED_MONTHLY_TICKS,
    "monthlyPlays": [-1] * STORED_MONTHLY_TICKS,
    "monthlyPlays24h": [-1] * STORED_MONTHLY_TICKS,
    "monthlyUniquePlays24h": [-1] * STORED_MONTHLY_TICKS,
    "monthlyTimestamps": [None] * STORED_MONTHLY_TICKS,
    "athPlayerCount": 0,
    "athPlayerCountAt": None,
    "athPlays24h": 0,
    "athPlays24hAt": None,
    "athUniquePlays24h": 0,
    "athUniquePlays24hAt": None,
}

def insert_game(raw_data):
    game_data = raw_data["game"]
    live_stats = game_data["liveStats"]
    organization = game_data["organization"]

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "game" ("id", "slug", "slugProperCase", "name", "description", "iconImageId", "organizationId", "createdAt", "visibility", "lastVersionUpdate", "archivedAt", "loadingScreenImageId", "logoImageId", "videoId", "links", "plays", "favorites", "plays24h", "uniquePlays24h", "platforms", "liveStats", "gameStats") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (game_data["id"], game_data["slug"], game_data["slugProperCase"], game_data["name"], game_data["description"], game_data["iconImageId"], organization["id"], game_data["createdAt"], game_data["visibility"], game_data["lastVersionUpdate"], game_data["archivedAt"], game_data["loadingScreenImageId"], game_data["logoImageId"], game_data["videoId"], Jsonb(game_data["links"]), game_data["plays"], game_data["favorites"], game_data["plays24h"], game_data["uniquePlays24h"], Jsonb(game_data["platforms"]), Jsonb(live_stats), Jsonb(default_stats))
    )
    db.commit()
    upload_to_spaces("airspy", game_data["iconImageId"], get_image_url(game_data["iconImageId"]))
    embed = build_embed(
        "\U0001F195 New Airspy Game Tracked",
        fields=[("Game", game_data["name"]), ("Organization", organization["name"])],
        thumbnail_url=get_image_cdn_url("airspy", game_data["iconImageId"])
    )
    send_discord_notification("airspy_game_created", embed=embed)
    return f"Inserted game: {game_data["id"]}"

def get_tick_data():
    tick_data = get_matching_row("json", {"id": "airship_tick_data"})
    if tick_data:
        tick_data = tick_data["data"]
    if not tick_data:
        db = get_db()
        cursor = db.cursor()
        tick_data = {
            "tick": 0,
            "lastTick": time.time() * AIRSPY_SPEED,
            "dailyTick": 0,
            "lastDailyTick": time.time() * AIRSPY_SPEED,
            "monthlyTick": 0,
            "lastMonthlyTick": time.time() * AIRSPY_SPEED
        }
        cursor.execute(
            'INSERT INTO "json" ("id", "data") VALUES (%s, %s)',
            ("airship_tick_data", Jsonb(tick_data))
        )
        db.commit()

    return tick_data


def set_tick_data(tick_data):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "json" SET "data" = %s WHERE "id" = %s',
        (Jsonb(tick_data), "airship_tick_data")
    )
    db.commit()

def get_airspy_settings():
    settings = get_matching_row("json", {"id": "airspy_settings"})
    if settings:
        return settings["data"]

    db = get_db()
    cursor = db.cursor()
    settings = {"gamesUpdatedAfter": None}
    cursor.execute(
        'INSERT INTO "json" ("id", "data") VALUES (%s, %s)',
        ("airspy_settings", Jsonb(settings))
    )
    db.commit()
    return settings

def set_airspy_settings(settings):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE "json" SET "data" = %s WHERE "id" = %s',
        (Jsonb(settings), "airspy_settings")
    )
    db.commit()

def organize_game_data(raw_data):
    game_data = raw_data["game"]
    live_stats = game_data["liveStats"]
    organization = game_data["organization"]
    return {
        "id": game_data.get("id"),
        "slug": game_data.get("slug"),
        "slugProperCase": game_data.get("slugProperCase"),
        "name": game_data.get("name"),
        "description": game_data.get("description"),
        "iconImageId": game_data.get("iconImageId"),
        "organizationId": organization.get("id"),
        "createdAt": datetime.fromisoformat(game_data.get("createdAt").replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S.%f") if game_data.get("createdAt") else None,
        "visibility": game_data.get("visibility"),
        "lastVersionUpdate": datetime.fromisoformat(game_data.get("lastVersionUpdate").replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S.%f") if game_data.get("lastVersionUpdate") else None,
        "archivedAt": datetime.fromisoformat(game_data.get("archivedAt").replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S.%f") if game_data.get("archivedAt") else None,
        "loadingScreenImageId": game_data.get("loadingScreenImageId"),
        "logoImageId": game_data.get("logoImageId"),
        "videoId": game_data.get("videoId"),
        "links": game_data.get("links"),
        "plays": game_data.get("plays"),
        "favorites": game_data.get("favorites"),
        "plays24h": game_data.get("plays24h"),
        "uniquePlays24h": game_data.get("uniquePlays24h"),
        "platforms": game_data.get("platforms"),
        "liveStats": live_stats
    }

def update_game(raw_data):
    """Insert the game if it doesn't exist yet, otherwise update only the fields that changed."""
    game_data = raw_data["game"]
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT * FROM "game" WHERE "id" = %s', (game_data["id"],))
    existing_row = cursor.fetchone()

    if not existing_row:
        return insert_game(raw_data)

    changed_fields = {}
    new_data = organize_game_data(raw_data)

    for key, new_value in new_data.items():
        if key in existing_row.keys() and str(existing_row[key]) != str(new_value):
            changed_fields[key] = new_value

    if not changed_fields:
        return f"No changes detected for game: {game_data["id"]}"

    set_clause = ", ".join([f'"{column}" = %s' for column in changed_fields.keys()])

    query_params = [Jsonb(value) if isinstance(value, (dict, list)) else value for value in changed_fields.values()] + [game_data["id"]]

    sql_query = f'UPDATE "game" SET {set_clause} WHERE "id" = %s'
    cursor.execute(sql_query, query_params)

    db.commit()

    if "lastVersionUpdate" in changed_fields:
        embed = build_embed(
            "\U0001F504 Airspy Game Updated",
            fields=[("Game", game_data["name"]), ("Organization", game_data["organization"]["name"])],
            thumbnail_url=get_image_cdn_url("airspy", game_data["iconImageId"])
        )
        send_discord_notification("airspy_game_version_updated", embed=embed)

    return f"Updated game: {game_data["id"]}, {changed_fields}"


def organize_organization_data(raw_data):
    return {
        "id": raw_data.get("id"),
        "slug": raw_data.get("slug"),
        "slugProperCase": raw_data.get("slugProperCase"),
        "name": raw_data.get("name"),
        "description": raw_data.get("description"),
        "iconImageId": raw_data.get("iconImageId"),
        "createdAt": datetime.fromisoformat(raw_data.get("createdAt").replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S.%f") if raw_data.get("createdAt") else None,
        "adminBanned": raw_data.get("adminBanned")
    }

def insert_organization(raw_data):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO "organization" ("id", "slug", "slugProperCase", "name", "description", "iconImageId", "createdAt", "adminBanned", "orgStats") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (raw_data["id"], raw_data["slug"], raw_data["slugProperCase"], raw_data["name"], raw_data["description"], raw_data["iconImageId"], raw_data["createdAt"], raw_data["adminBanned"], Jsonb(default_stats))
    )
    db.commit()
    upload_to_spaces("airspy", raw_data["iconImageId"], get_image_url(raw_data["iconImageId"]))
    embed = build_embed(
        "\U0001F195 New Airspy Organization Tracked",
        fields=[("Organization", raw_data["name"])],
        thumbnail_url=get_image_cdn_url("airspy", raw_data["iconImageId"])
    )
    send_discord_notification("airspy_organization_created", embed=embed)

    return f"Inserted organization: {raw_data["id"]}"

def update_organization(raw_data):
    """Insert the organization if it doesn't exist yet, otherwise update only the fields that changed."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f'SELECT * FROM "organization" WHERE "id" = %s', (raw_data["id"],))
    existing_row = cursor.fetchone()
    if not existing_row:
        return insert_organization(raw_data)
    changed_fields = {}
    new_data = organize_organization_data(raw_data)
    for key, new_value in new_data.items():
        if key in existing_row.keys() and str(existing_row[key]) != str(new_value):
            changed_fields[key] = new_value
    if not changed_fields:
        return f"No changes detected for organization: {raw_data['id']}"
    set_clause = ", ".join([f'"{column}" = %s' for column in changed_fields.keys()])
        
    query_params = list(changed_fields.values()) + [raw_data["id"]]
        
    sql_query = f'UPDATE "organization" SET {set_clause} WHERE "id" = %s'
    cursor.execute(sql_query, query_params)
    db.commit()
    return f"Updated organization: {raw_data["id"]}, {changed_fields}"

def update_game_stats(game_id, stats):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f'UPDATE "game" SET "gameStats" = %s WHERE "id" = %s', (Jsonb(stats), game_id))
    db.commit()

def update_organization_stats(org_id, stats):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f'UPDATE "organization" SET "orgStats" = %s WHERE id = %s', (Jsonb(stats), org_id))
    db.commit()

def get_all_games():
    """Admin listing of every tracked game, including ones hidden from Airspy."""
    db = get_db()
    cursor = db.cursor()
    query = (
        'SELECT "game"."id", "game"."name", "game"."iconImageId", "game"."hiddenFromAirspy", '
        '"game"."organizationId", "game"."lastVersionUpdate", "organization"."name" AS "organizationName" '
        'FROM "game" JOIN "organization" ON "game"."organizationId" = "organization"."id" '
        'ORDER BY "game"."lastVersionUpdate" DESC'
    )
    return cursor.execute(query).fetchall()

def reset_airspy_data():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('TRUNCATE TABLE "game", "organization"')
    cursor.execute('DELETE FROM "json" WHERE "id" = %s', ("airship_tick_data",))
    db.commit()

@click.command('reset-airspy-db')
@click.option('--yes', is_flag=True, help='Skip the confirmation prompt.')
def reset_airspy_db_command(yes):
    if not yes and not click.confirm('This will permanently delete all Airspy games, organizations, and tick data. Continue?'):
        click.echo('Aborted.')
        return

    reset_airspy_data()
    click.echo('Reset all Airspy data.')

def _leading_gap_length(timestamps):
    """Index of the first real timestamp in a series. Everything before it
    is never-ticked default padding (or so early in the game's history it
    can't be told apart from padding) - it should stay excluded from charts
    (-1) rather than being turned into a fabricated data point at index 0."""
    for i, t in enumerate(timestamps):
        if t is not None:
            return i
    return len(timestamps)

def _fix_player_count_series(values, skip):
    """A -1 (no data) reading becomes 0 - we can't assume anyone was online -
    except the leading `skip` entries, which are left as -1 (excluded)."""
    return [-1] * skip + [0 if v == -1 else v for v in values[skip:]]

def _fix_monotonic_series(values, skip):
    """For a lifetime counter like 'plays' that should never decrease: carry
    a -1 gap forward, and clamp any anomalous drop back up to the running
    max, in one forward pass. The leading `skip` entries are left as -1."""
    fixed = [-1] * skip
    last = 0
    for v in values[skip:]:
        value = last if v == -1 else max(v, last)
        fixed.append(value)
        last = value
    return fixed

def _fix_carry_forward_series(values, skip):
    """Replace -1 gaps with the last known real reading (0 if none yet). The
    leading `skip` entries are left as -1."""
    fixed = [-1] * skip
    last = 0
    for v in values[skip:]:
        if v == -1:
            fixed.append(last)
        else:
            fixed.append(v)
            last = v
    return fixed

def _fix_timestamps(timestamps, skip, step_seconds, now_dt):
    """Synthesize a real timestamp for every gap entry after the leading
    padding (position i is `(len - 1 - i) * step_seconds` before now, since
    the series always ends at "now" at a fixed cadence), instead of leaving
    it None - a plotted gap point needs a real time to label on the chart."""
    fixed = list(timestamps[:skip])
    real = timestamps[skip:]
    n = len(real)
    for i in range(n):
        if real[i] is not None:
            fixed.append(real[i])
        else:
            offset = n - 1 - i
            synthesized = now_dt - timedelta(seconds=step_seconds * offset)
            fixed.append(synthesized.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    return fixed

def _fix_stats(stats, now_dt):
    tick_skip = _leading_gap_length(stats["timestamps"])
    stats["playerCounts"] = _fix_player_count_series(stats["playerCounts"], tick_skip)
    stats["plays"] = _fix_monotonic_series(stats["plays"], tick_skip)
    stats["plays24h"] = _fix_carry_forward_series(stats["plays24h"], tick_skip)
    stats["uniquePlays24h"] = _fix_carry_forward_series(stats["uniquePlays24h"], tick_skip)
    stats["timestamps"] = _fix_timestamps(stats["timestamps"], tick_skip, 60 * AIRSPY_UPDATE_TIMEOUT, now_dt)

    daily_skip = _leading_gap_length(stats["dailyTimestamps"])
    stats["dailyPlayerCounts"] = _fix_player_count_series(stats["dailyPlayerCounts"], daily_skip)
    stats["dailyPlays"] = _fix_monotonic_series(stats["dailyPlays"], daily_skip)
    stats["dailyPlays24h"] = _fix_carry_forward_series(stats["dailyPlays24h"], daily_skip)
    stats["dailyUniquePlays24h"] = _fix_carry_forward_series(stats["dailyUniquePlays24h"], daily_skip)
    stats["dailyTimestamps"] = _fix_timestamps(stats["dailyTimestamps"], daily_skip, 86400, now_dt)

    monthly_skip = _leading_gap_length(stats["monthlyTimestamps"])
    stats["monthlyPlayerCounts"] = _fix_player_count_series(stats["monthlyPlayerCounts"], monthly_skip)
    stats["monthlyPlays"] = _fix_monotonic_series(stats["monthlyPlays"], monthly_skip)
    stats["monthlyPlays24h"] = _fix_carry_forward_series(stats["monthlyPlays24h"], monthly_skip)
    stats["monthlyUniquePlays24h"] = _fix_carry_forward_series(stats["monthlyUniquePlays24h"], monthly_skip)
    stats["monthlyTimestamps"] = _fix_timestamps(stats["monthlyTimestamps"], monthly_skip, 2592000, now_dt)
    return stats

def fix_airspy_data():
    """Rewrite every tracked game/organization's stats to apply the current
    gap/anomaly rules retroactively: -1 (no data) becomes 0 for player
    counts, a carried-forward value for rolling metrics, and the lifetime
    'plays' counter has any anomalous drop clamped back up. Safe to re-run -
    already-clean data is left unchanged."""
    db = get_db()
    cursor = db.cursor()
    now_dt = datetime.now(timezone.utc)

    cursor.execute('SELECT "id", "gameStats" FROM "game"')
    games = cursor.fetchall()
    for game in games:
        update_game_stats(game["id"], _fix_stats(game["gameStats"], now_dt))

    cursor.execute('SELECT "id", "orgStats" FROM "organization"')
    organizations = cursor.fetchall()
    for organization in organizations:
        update_organization_stats(organization["id"], _fix_stats(organization["orgStats"], now_dt))

    return len(games), len(organizations)

@click.command('fix-airspy-data')
@click.option('--yes', is_flag=True, help='Skip the confirmation prompt.')
def fix_airspy_data_command(yes):
    if not yes and not click.confirm('This will rewrite gameStats/orgStats for every tracked game and organization to fix legacy gaps and anomalous dips. Continue?'):
        click.echo('Aborted.')
        return

    game_count, org_count = fix_airspy_data()
    click.echo(f'Fixed stats for {game_count} games and {org_count} organizations.')