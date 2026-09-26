import click, time
from Site.code.database.main import get_db, get_matching_row
from Site.code.database.cdn import upload_to_spaces
from Site.code.airspy.airship_urls import get_image_url
from Site.code.config import AIRSPY_SPEED, STORED_TICKS, STORED_DAILY_TICKS, STORED_MONTHLY_TICKS
from psycopg.types.json import Jsonb
from datetime import datetime

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