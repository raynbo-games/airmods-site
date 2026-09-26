from flask import Flask
import time, math
from datetime import datetime, timezone
from Site.code.airspy.airship_urls import request_games, request_game_id, get_image_url
from Site.code.airspy.database import update_game, update_organization, update_organization_stats, update_game_stats, get_tick_data, set_tick_data
from Site.code.config import AIRSPY_UPDATE_TIMEOUT, AIRSPY_SPEED
from Site.code.database.cdn import upload_to_spaces
from Site.code.database.main import get_matching_row, get_property_value

def tick_airspy_icons(app: Flask):
    """Scheduled task: mirror every tracked game/organization icon to the CDN."""
    game_image_ids = get_property_value("game", "iconImageId")
    organization_image_ids = get_property_value("organization", "iconImageId")
    for image_id in game_image_ids:
        upload_to_spaces("airspy", image_id, get_image_url(image_id))
    for image_id in organization_image_ids:
        upload_to_spaces("airspy", image_id, get_image_url(image_id))

def tick_airspy(app: Flask):
    """Scheduled task: pull live Airship stats and append a tick to every tracked
    game/organization, then roll ticks into daily/monthly buckets once due."""
    data = get_tick_data()

    missed_ticks = math.floor(((time.time() * AIRSPY_SPEED - data["lastTick"]) / 60) / AIRSPY_UPDATE_TIMEOUT)
    tick_count = 1 + missed_ticks
    current_tick_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    games = request_games()
    if games is None:
        app.logger.warning("Failed to fetch games.")
        return

    game_ids = get_property_value("game", "id")
    organization_ids = get_property_value("organization", "id")

    def process_game_data(game_data):
        if game_data["id"] not in game_ids:
            game_ids.append(game_data["id"])
        if game_data["organization"]["id"] not in organization_ids:
            organization_ids.append(game_data["organization"]["id"])

    for game_data in games["popular"]:
        process_game_data(game_data)
    for game_data in games["featured"]:
        process_game_data(game_data)
    for game_data in games["recentlyUpdated"]:
        process_game_data(game_data)

    organization_data = {}
    
    for game_id in game_ids:
        raw_data = request_game_id(game_id, liveStats=True)
        if raw_data is None:
            app.logger.warning(f"Failed to fetch game data for game_id: {game_id}")

            # A failed fetch still counts as tick_count ticks having passed for this
            # game - back it off with -1 placeholders like the missed_ticks case,
            # otherwise this game's arrays fall out of alignment with the shared
            # clock and its data desyncs from every other game's.
            game_data = get_matching_row("game", {"id": game_id})
            game_data['gameStats']["playerCounts"].extend([-1] * tick_count)
            game_data['gameStats']["plays"].extend([-1] * tick_count)
            game_data['gameStats']["plays24h"].extend([-1] * tick_count)
            game_data['gameStats']["uniquePlays24h"].extend([-1] * tick_count)
            game_data['gameStats']["timestamps"].extend([None] * tick_count)

            del game_data['gameStats']["playerCounts"][:tick_count]
            del game_data['gameStats']["plays"][:tick_count]
            del game_data['gameStats']["plays24h"][:tick_count]
            del game_data['gameStats']["uniquePlays24h"][:tick_count]
            del game_data['gameStats']["timestamps"][:tick_count]

            update_game_stats(game_data["id"], game_data['gameStats'])
            continue

        app.logger.debug(update_game(raw_data))
        game_data = get_matching_row("game", {"id": game_id})

        playerCount = raw_data["game"]["liveStats"]["playerCount"]
        plays = raw_data["game"]["plays"]
        plays24h = raw_data["game"]["plays24h"]
        uniquePlays24h = raw_data["game"]["uniquePlays24h"]

        if missed_ticks > 0:
            game_data['gameStats']["playerCounts"].extend([-1] * missed_ticks)
            game_data['gameStats']["plays"].extend([-1] * missed_ticks)
            game_data['gameStats']["plays24h"].extend([-1] * missed_ticks)
            game_data['gameStats']["uniquePlays24h"].extend([-1] * missed_ticks)
            game_data['gameStats']["timestamps"].extend([None] * missed_ticks)

        game_data['gameStats']["playerCounts"].append(playerCount)
        game_data['gameStats']["plays"].append(plays)
        game_data['gameStats']["plays24h"].append(plays24h)
        game_data['gameStats']["uniquePlays24h"].append(uniquePlays24h)
        game_data['gameStats']["timestamps"].append(current_tick_time)

        del game_data['gameStats']["playerCounts"][:tick_count]
        del game_data['gameStats']["plays"][:tick_count]
        del game_data['gameStats']["plays24h"][:tick_count]
        del game_data['gameStats']["uniquePlays24h"][:tick_count]
        del game_data['gameStats']["timestamps"][:tick_count]

        if playerCount > game_data["gameStats"]["athPlayerCount"]:
            game_data["gameStats"]["athPlayerCount"] = playerCount
            game_data["gameStats"]["athPlayerCountAt"] = current_tick_time
        if plays24h > game_data["gameStats"]["athPlays24h"]:
            game_data["gameStats"]["athPlays24h"] = plays24h
            game_data["gameStats"]["athPlays24hAt"] = current_tick_time
        if uniquePlays24h > game_data["gameStats"]["athUniquePlays24h"]:
            game_data["gameStats"]["athUniquePlays24h"] = uniquePlays24h
            game_data["gameStats"]["athUniquePlays24hAt"] = current_tick_time

        update_game_stats(game_data["id"], game_data['gameStats'])

        if raw_data["game"]["organization"]["id"] not in organization_data:
            organization_data[raw_data["game"]["organization"]["id"]] = {
                "data": raw_data["game"]["organization"],
                "orgStats": {
                    "playerCounts": playerCount,
                    "plays": plays,
                    "plays24h": plays24h,
                    "uniquePlays24h": uniquePlays24h,
                 }
            }
        else:
            organization_data[raw_data["game"]["organization"]["id"]]["orgStats"]["playerCounts"] += playerCount
            organization_data[raw_data["game"]["organization"]["id"]]["orgStats"]["plays"] += plays
            organization_data[raw_data["game"]["organization"]["id"]]["orgStats"]["plays24h"] += plays24h
            organization_data[raw_data["game"]["organization"]["id"]]["orgStats"]["uniquePlays24h"] += uniquePlays24h

    for orgId, current in organization_data.items():
        raw_data = current["data"]
        app.logger.debug(update_organization(raw_data))
        org_data = get_matching_row("organization", {"id": raw_data["id"]})

        playerCount = current["orgStats"]["playerCounts"]
        plays = current["orgStats"]["plays"]
        plays24h = current["orgStats"]["plays24h"]
        uniquePlays24h = current["orgStats"]["uniquePlays24h"]

        if missed_ticks > 0:
            org_data['orgStats']["playerCounts"].extend([-1] * missed_ticks)
            org_data['orgStats']["plays"].extend([-1] * missed_ticks)
            org_data['orgStats']["plays24h"].extend([-1] * missed_ticks)
            org_data['orgStats']["uniquePlays24h"].extend([-1] * missed_ticks)
            org_data['orgStats']["timestamps"].extend([None] * missed_ticks)

        org_data['orgStats']["playerCounts"].append(playerCount)
        org_data['orgStats']["plays"].append(plays)
        org_data['orgStats']["plays24h"].append(plays24h)
        org_data['orgStats']["uniquePlays24h"].append(uniquePlays24h)
        org_data['orgStats']["timestamps"].append(current_tick_time)

        del org_data['orgStats']["playerCounts"][:tick_count]
        del org_data['orgStats']["plays"][:tick_count]
        del org_data['orgStats']["plays24h"][:tick_count]
        del org_data['orgStats']["uniquePlays24h"][:tick_count]
        del org_data['orgStats']["timestamps"][:tick_count]

        if playerCount > org_data["orgStats"]["athPlayerCount"]:
            org_data["orgStats"]["athPlayerCount"] = playerCount
            org_data["orgStats"]["athPlayerCountAt"] = current_tick_time
        if plays24h > org_data["orgStats"]["athPlays24h"]:
            org_data["orgStats"]["athPlays24h"] = plays24h
            org_data["orgStats"]["athPlays24hAt"] = current_tick_time
        if uniquePlays24h > org_data["orgStats"]["athUniquePlays24h"]:
            org_data["orgStats"]["athUniquePlays24h"] = uniquePlays24h
            org_data["orgStats"]["athUniquePlays24hAt"] = current_tick_time

        update_organization_stats(org_data["id"], org_data['orgStats'])

    data["tick"] += tick_count
    data["lastTick"] = time.time() * AIRSPY_SPEED

    days = math.floor((time.time() * AIRSPY_SPEED - data["lastDailyTick"]) / 86400)

    if days < 1:
        set_tick_data(data)
        return

    missed_days = days - 1
    
    for game_id in game_ids:
        game_data = get_matching_row("game", {"id": game_id})

        if missed_days > 0:
            game_data['gameStats']["dailyPlayerCounts"].extend([-1] * missed_days)
            game_data['gameStats']["dailyPlays"].extend([-1] * missed_days)
            game_data['gameStats']["dailyPlays24h"].extend([-1] * missed_days)
            game_data['gameStats']["dailyUniquePlays24h"].extend([-1] * missed_days)
            game_data['gameStats']["dailyTimestamps"].extend([None] * missed_days)

        filtered = [num for num in game_data['gameStats']["playerCounts"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        game_data['gameStats']["dailyPlayerCounts"].append(value)

        filtered = [num for num in game_data['gameStats']["plays"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        game_data['gameStats']["dailyPlays"].append(value)

        filtered = [num for num in game_data['gameStats']["plays24h"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        game_data['gameStats']["dailyPlays24h"].append(value)

        filtered = [num for num in game_data['gameStats']["uniquePlays24h"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        game_data['gameStats']["dailyUniquePlays24h"].append(value)

        filtered = [t for t in game_data['gameStats']["timestamps"] if t is not None]
        game_data['gameStats']["dailyTimestamps"].append(filtered[-1] if len(filtered) >= 1 else None)

        del game_data['gameStats']["dailyPlayerCounts"][:days]
        del game_data['gameStats']["dailyPlays"][:days]
        del game_data['gameStats']["dailyPlays24h"][:days]
        del game_data['gameStats']["dailyUniquePlays24h"][:days]
        del game_data['gameStats']["dailyTimestamps"][:days]

        update_game_stats(game_id, game_data['gameStats'])

    for org_id in organization_ids:
        org_data = get_matching_row("organization", {"id": org_id})

        if missed_days > 0:
            org_data['orgStats']["dailyPlayerCounts"].extend([-1] * missed_days)
            org_data['orgStats']["dailyPlays"].extend([-1] * missed_days)
            org_data['orgStats']["dailyPlays24h"].extend([-1] * missed_days)
            org_data['orgStats']["dailyUniquePlays24h"].extend([-1] * missed_days)
            org_data['orgStats']["dailyTimestamps"].extend([None] * missed_days)

        filtered = [num for num in org_data['orgStats']["playerCounts"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        org_data['orgStats']["dailyPlayerCounts"].append(value)

        filtered = [num for num in org_data['orgStats']["plays"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        org_data['orgStats']["dailyPlays"].append(value)

        filtered = [num for num in org_data['orgStats']["plays24h"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        org_data['orgStats']["dailyPlays24h"].append(value)

        filtered = [num for num in org_data['orgStats']["uniquePlays24h"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        org_data['orgStats']["dailyUniquePlays24h"].append(value)

        filtered = [t for t in org_data['orgStats']["timestamps"] if t is not None]
        org_data['orgStats']["dailyTimestamps"].append(filtered[-1] if len(filtered) >= 1 else None)

        del org_data['orgStats']["dailyPlayerCounts"][:days]
        del org_data['orgStats']["dailyPlays"][:days]
        del org_data['orgStats']["dailyPlays24h"][:days]
        del org_data['orgStats']["dailyUniquePlays24h"][:days]
        del org_data['orgStats']["dailyTimestamps"][:days]

        update_organization_stats(org_id, org_data['orgStats'])

    data["dailyTick"] += days
    data["lastDailyTick"] = time.time() * AIRSPY_SPEED

    months = math.floor((time.time() * AIRSPY_SPEED - data["lastMonthlyTick"]) / 2592000)

    if months < 1:
        set_tick_data(data)
        return

    missed_months = months - 1

    for game_id in game_ids:
        game_data = get_matching_row("game", {"id": game_id})

        if missed_months > 0:
            game_data['gameStats']["monthlyPlayerCounts"].extend([-1] * missed_months)
            game_data['gameStats']["monthlyPlays"].extend([-1] * missed_months)
            game_data['gameStats']["monthlyPlays24h"].extend([-1] * missed_months)
            game_data['gameStats']["monthlyUniquePlays24h"].extend([-1] * missed_months)
            game_data['gameStats']["monthlyTimestamps"].extend([None] * missed_months)

        filtered = [num for num in game_data['gameStats']["dailyPlayerCounts"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        game_data['gameStats']["monthlyPlayerCounts"].append(value)

        filtered = [num for num in game_data['gameStats']["dailyPlays"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        game_data['gameStats']["monthlyPlays"].append(value)

        filtered = [num for num in game_data['gameStats']["dailyPlays24h"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        game_data['gameStats']["monthlyPlays24h"].append(value)

        filtered = [num for num in game_data['gameStats']["dailyUniquePlays24h"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        game_data['gameStats']["monthlyUniquePlays24h"].append(value)

        filtered = [t for t in game_data['gameStats']["dailyTimestamps"] if t is not None]
        game_data['gameStats']["monthlyTimestamps"].append(filtered[-1] if len(filtered) >= 1 else None)

        del game_data['gameStats']["monthlyPlayerCounts"][:months]
        del game_data['gameStats']["monthlyPlays"][:months]
        del game_data['gameStats']["monthlyPlays24h"][:months]
        del game_data['gameStats']["monthlyUniquePlays24h"][:months]
        del game_data['gameStats']["monthlyTimestamps"][:months]

        update_game_stats(game_id, game_data['gameStats'])

    for org_id in organization_ids:
        org_data = get_matching_row("organization", {"id": org_id})

        if missed_months > 0:
            org_data['orgStats']["monthlyPlayerCounts"].extend([-1] * missed_months)
            org_data['orgStats']["monthlyPlays"].extend([-1] * missed_months)
            org_data['orgStats']["monthlyPlays24h"].extend([-1] * missed_months)
            org_data['orgStats']["monthlyUniquePlays24h"].extend([-1] * missed_months)
            org_data['orgStats']["monthlyTimestamps"].extend([None] * missed_months)

        filtered = [num for num in org_data['orgStats']["dailyPlayerCounts"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        org_data['orgStats']["monthlyPlayerCounts"].append(value)

        filtered = [num for num in org_data['orgStats']["dailyPlays"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        org_data['orgStats']["monthlyPlays"].append(value)

        filtered = [num for num in org_data['orgStats']["dailyPlays24h"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        org_data['orgStats']["monthlyPlays24h"].append(value)

        filtered = [num for num in org_data['orgStats']["dailyUniquePlays24h"] if num != -1]
        if (len(filtered) >= 1): value = max(filtered)
        else: value = -1
        org_data['orgStats']["monthlyUniquePlays24h"].append(value)

        filtered = [t for t in org_data['orgStats']["dailyTimestamps"] if t is not None]
        org_data['orgStats']["monthlyTimestamps"].append(filtered[-1] if len(filtered) >= 1 else None)

        del org_data['orgStats']["monthlyPlayerCounts"][:months]
        del org_data['orgStats']["monthlyPlays"][:months]
        del org_data['orgStats']["monthlyPlays24h"][:months]
        del org_data['orgStats']["monthlyUniquePlays24h"][:months]
        del org_data['orgStats']["monthlyTimestamps"][:months]

        update_organization_stats(org_id, org_data['orgStats'])

    data["monthlyTick"] += months
    data["lastMonthlyTick"] = time.time() * AIRSPY_SPEED

    set_tick_data(data)

    return

default_stats = {
    "playerCounts": [],
    "plays": [],
    "plays24h": [],
    "uniquePlays24h": [],
    "timestamps": [],
    "dailyPlayerCounts": [],
    "dailyPlays": [],
    "dailyPlays24h": [],
    "dailyUniquePlays24h": [],
    "dailyTimestamps": [],
    "monthlyPlayerCounts": [],
    "monthlyPlays": [],
    "monthlyPlays24h": [],
    "monthlyUniquePlays24h": [],
    "monthlyTimestamps": [],
    "athPlayerCount": 0,
    "athPlayerCountAt": None,
    "athPlays24h": 0,
    "athPlays24hAt": None,
    "athUniquePlays24h": 0,
    "athUniquePlays24hAt": None,
}