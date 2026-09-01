from flask import Flask
import time, math
from datetime import datetime, timezone
from Site.code.airspy.airship_urls import request_games, request_game_id, get_image_url
from Site.code.airspy.database import update_game, update_organization, update_organization_stats, update_game_stats, get_tick_data, set_tick_data
from Site.code.config import AIRSPY_UPDATE_TIMEOUT, AIRSPY_SPEED
from Site.code.database.cdn import upload_to_spaces
from Site.code.database.main import get_matching_row, get_property_value

def tick_airspy_icons(app: Flask):
    game_image_ids = get_property_value("game", "iconImageId")
    organization_image_ids = get_property_value("organization", "iconImageId")
    for image_id in game_image_ids:
        upload_to_spaces("airspy", image_id, get_image_url(image_id))
    for image_id in organization_image_ids:
        upload_to_spaces("airspy", image_id, get_image_url(image_id))

def tick_airspy(app: Flask):
    data = get_tick_data()

    missedTicks = math.floor(((time.time() * AIRSPY_SPEED - data["lastTick"]) / 60) / AIRSPY_UPDATE_TIMEOUT)
    tickCount = 1 + missedTicks
    current_tick_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    games = request_games()
    if games is None:
        app.logger.warning("Failed to fetch games.")
        return

    game_ids = get_property_value("game", "id")
    organization_ids = get_property_value("organization", "id")

    def process_game_data(gameData):
        if gameData["id"] not in game_ids:
            game_ids.append(gameData["id"])
        if gameData["organization"]["id"] not in organization_ids:
            organization_ids.append(gameData["organization"]["id"])

    for gameData in games["popular"]:
        process_game_data(gameData)
    for gameData in games["featured"]:
        process_game_data(gameData)
    for gameData in games["recentlyUpdated"]:
        process_game_data(gameData)

    organization_data = {}
    
    for game_id in game_ids:
        raw_data = request_game_id(game_id, liveStats=True)
        if raw_data is None:
            app.logger.warning(f"Failed to fetch game data for game_id: {game_id}")
            continue

        app.logger.debug(update_game(raw_data))
        gameData = get_matching_row("game", {"id": game_id})

        playerCount = raw_data["game"]["liveStats"]["playerCount"]
        plays = raw_data["game"]["plays"]
        plays24h = raw_data["game"]["plays24h"]
        uniquePlays24h = raw_data["game"]["uniquePlays24h"]

        if missedTicks > 0:
            gameData['gameStats']["playerCounts"].extend([-1] * missedTicks)
            gameData['gameStats']["plays"].extend([-1] * missedTicks)
            gameData['gameStats']["plays24h"].extend([-1] * missedTicks)
            gameData['gameStats']["uniquePlays24h"].extend([-1] * missedTicks)
            gameData['gameStats']["timestamps"].extend([None] * missedTicks)

        gameData['gameStats']["playerCounts"].append(playerCount)
        gameData['gameStats']["plays"].append(plays)
        gameData['gameStats']["plays24h"].append(plays24h)
        gameData['gameStats']["uniquePlays24h"].append(uniquePlays24h)
        gameData['gameStats']["timestamps"].append(current_tick_time)

        del gameData['gameStats']["playerCounts"][:tickCount]
        del gameData['gameStats']["plays"][:tickCount]
        del gameData['gameStats']["plays24h"][:tickCount]
        del gameData['gameStats']["uniquePlays24h"][:tickCount]
        del gameData['gameStats']["timestamps"][:tickCount]

        if playerCount > gameData["gameStats"]["athPlayerCount"]:
            gameData["gameStats"]["athPlayerCount"] = playerCount
            gameData["gameStats"]["athPlayerCountAt"] = current_tick_time
        if plays24h > gameData["gameStats"]["athPlays24h"]:
            gameData["gameStats"]["athPlays24h"] = plays24h
            gameData["gameStats"]["athPlays24hAt"] = current_tick_time
        if uniquePlays24h > gameData["gameStats"]["athUniquePlays24h"]:
            gameData["gameStats"]["athUniquePlays24h"] = uniquePlays24h
            gameData["gameStats"]["athUniquePlays24hAt"] = current_tick_time

        update_game_stats(gameData["id"], gameData['gameStats'])

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
        orgData = get_matching_row("organization", {"id": raw_data["id"]})

        playerCount = current["orgStats"]["playerCounts"]
        plays = current["orgStats"]["plays"]
        plays24h = current["orgStats"]["plays24h"]
        uniquePlays24h = current["orgStats"]["uniquePlays24h"]

        if missedTicks > 0:
            orgData['orgStats']["playerCounts"].extend([-1] * missedTicks)
            orgData['orgStats']["plays"].extend([-1] * missedTicks)
            orgData['orgStats']["plays24h"].extend([-1] * missedTicks)
            orgData['orgStats']["uniquePlays24h"].extend([-1] * missedTicks)
            orgData['orgStats']["timestamps"].extend([None] * missedTicks)

        orgData['orgStats']["playerCounts"].append(playerCount)
        orgData['orgStats']["plays"].append(plays)
        orgData['orgStats']["plays24h"].append(plays24h)
        orgData['orgStats']["uniquePlays24h"].append(uniquePlays24h)
        orgData['orgStats']["timestamps"].append(current_tick_time)

        del orgData['orgStats']["playerCounts"][:tickCount]
        del orgData['orgStats']["plays"][:tickCount]
        del orgData['orgStats']["plays24h"][:tickCount]
        del orgData['orgStats']["uniquePlays24h"][:tickCount]
        del orgData['orgStats']["timestamps"][:tickCount]

        if playerCount > orgData["orgStats"]["athPlayerCount"]:
            orgData["orgStats"]["athPlayerCount"] = playerCount
            orgData["orgStats"]["athPlayerCountAt"] = current_tick_time
        if plays24h > orgData["orgStats"]["athPlays24h"]:
            orgData["orgStats"]["athPlays24h"] = plays24h
            orgData["orgStats"]["athPlays24hAt"] = current_tick_time
        if uniquePlays24h > orgData["orgStats"]["athUniquePlays24h"]:
            orgData["orgStats"]["athUniquePlays24h"] = uniquePlays24h
            orgData["orgStats"]["athUniquePlays24hAt"] = current_tick_time

        update_organization_stats(orgData["id"], orgData['orgStats'])

    data["tick"] += tickCount
    data["lastTick"] = time.time() * AIRSPY_SPEED

    days = math.floor((time.time() * AIRSPY_SPEED - data["lastDailyTick"]) / 86400)

    if days < 1:
        set_tick_data(data)
        return

    missedDays = days - 1
    
    for game_id in game_ids:
        gameData = get_matching_row("game", {"id": game_id})

        if missedDays > 0:
            gameData['gameStats']["dailyPlayerCounts"].extend([-1] * missedDays)
            gameData['gameStats']["dailyPlays"].extend([-1] * missedDays)
            gameData['gameStats']["dailyPlays24h"].extend([-1] * missedDays)
            gameData['gameStats']["dailyUniquePlays24h"].extend([-1] * missedDays)
            gameData['gameStats']["dailyTimestamps"].extend([None] * missedDays)

        filtered = [num for num in gameData['gameStats']["playerCounts"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        gameData['gameStats']["dailyPlayerCounts"].append(value)

        filtered = [num for num in gameData['gameStats']["plays"] if num != -1]
        if (len(filtered) >= 1): value = filtered[-1]
        else: value = -1
        gameData['gameStats']["dailyPlays"].append(value)

        filtered = [num for num in gameData['gameStats']["plays24h"] if num != -1]
        if (len(filtered) >= 1): value = filtered[-1]
        else: value = -1
        gameData['gameStats']["dailyPlays24h"].append(value)

        filtered = [num for num in gameData['gameStats']["uniquePlays24h"] if num != -1]
        if (len(filtered) >= 1): value = filtered[-1]
        else: value = -1
        gameData['gameStats']["dailyUniquePlays24h"].append(value)

        filtered = [t for t in gameData['gameStats']["timestamps"] if t is not None]
        gameData['gameStats']["dailyTimestamps"].append(filtered[-1] if len(filtered) >= 1 else None)

        del gameData['gameStats']["dailyPlayerCounts"][:days]
        del gameData['gameStats']["dailyPlays"][:days]
        del gameData['gameStats']["dailyPlays24h"][:days]
        del gameData['gameStats']["dailyUniquePlays24h"][:days]
        del gameData['gameStats']["dailyTimestamps"][:days]

        update_game_stats(game_id, gameData['gameStats'])

    for org_id in organization_ids:
        orgData = get_matching_row("organization", {"id": org_id})

        if missedDays > 0:
            orgData['orgStats']["dailyPlayerCounts"].extend([-1] * missedDays)
            orgData['orgStats']["dailyPlays"].extend([-1] * missedDays)
            orgData['orgStats']["dailyPlays24h"].extend([-1] * missedDays)
            orgData['orgStats']["dailyUniquePlays24h"].extend([-1] * missedDays)
            orgData['orgStats']["dailyTimestamps"].extend([None] * missedDays)

        filtered = [num for num in orgData['orgStats']["playerCounts"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        orgData['orgStats']["dailyPlayerCounts"].append(value)

        filtered = [num for num in orgData['orgStats']["plays"] if num != -1]
        if (len(filtered) >= 1): value = filtered[-1]
        else: value = -1
        orgData['orgStats']["dailyPlays"].append(value)

        filtered = [num for num in orgData['orgStats']["plays24h"] if num != -1]
        if (len(filtered) >= 1): value = filtered[-1]
        else: value = -1
        orgData['orgStats']["dailyPlays24h"].append(value)

        filtered = [num for num in orgData['orgStats']["uniquePlays24h"] if num != -1]
        if (len(filtered) >= 1): value = filtered[-1]
        else: value = -1
        orgData['orgStats']["dailyUniquePlays24h"].append(value)

        filtered = [t for t in orgData['orgStats']["timestamps"] if t is not None]
        orgData['orgStats']["dailyTimestamps"].append(filtered[-1] if len(filtered) >= 1 else None)

        del orgData['orgStats']["dailyPlayerCounts"][:days]
        del orgData['orgStats']["dailyPlays"][:days]
        del orgData['orgStats']["dailyPlays24h"][:days]
        del orgData['orgStats']["dailyUniquePlays24h"][:days]
        del orgData['orgStats']["dailyTimestamps"][:days]

        update_organization_stats(org_id, orgData['orgStats'])

    data["dailyTick"] += days
    data["lastDailyTick"] = time.time() * AIRSPY_SPEED

    months = math.floor((time.time() * AIRSPY_SPEED - data["lastMonthlyTick"]) / 2592000)

    if months < 1:
        set_tick_data(data)
        return

    missedMonths = months - 1

    for game_id in game_ids:
        gameData = get_matching_row("game", {"id": game_id})

        if missedMonths > 0:
            gameData['gameStats']["monthlyPlayerCounts"].extend([-1] * missedMonths)
            gameData['gameStats']["monthlyPlays"].extend([-1] * missedMonths)
            gameData['gameStats']["monthlyPlays24h"].extend([-1] * missedMonths)
            gameData['gameStats']["monthlyUniquePlays24h"].extend([-1] * missedMonths)
            gameData['gameStats']["monthlyTimestamps"].extend([None] * missedMonths)

        filtered = [num for num in gameData['gameStats']["dailyPlayerCounts"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        gameData['gameStats']["monthlyPlayerCounts"].append(value)

        filtered = [num for num in gameData['gameStats']["dailyPlays"] if num != -1]
        if (len(filtered) >= 1): value = filtered[-1]
        else: value = -1
        gameData['gameStats']["monthlyPlays"].append(value)

        filtered = [num for num in gameData['gameStats']["dailyPlays24h"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        gameData['gameStats']["monthlyPlays24h"].append(value)

        filtered = [num for num in gameData['gameStats']["dailyUniquePlays24h"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        gameData['gameStats']["monthlyUniquePlays24h"].append(value)

        filtered = [t for t in gameData['gameStats']["dailyTimestamps"] if t is not None]
        gameData['gameStats']["monthlyTimestamps"].append(filtered[-1] if len(filtered) >= 1 else None)

        del gameData['gameStats']["monthlyPlayerCounts"][:months]
        del gameData['gameStats']["monthlyPlays"][:months]
        del gameData['gameStats']["monthlyPlays24h"][:months]
        del gameData['gameStats']["monthlyUniquePlays24h"][:months]
        del gameData['gameStats']["monthlyTimestamps"][:months]

        update_game_stats(game_id, gameData['gameStats'])

    for org_id in organization_ids:
        orgData = get_matching_row("organization", {"id": org_id})

        if missedMonths > 0:
            orgData['orgStats']["monthlyPlayerCounts"].extend([-1] * missedMonths)
            orgData['orgStats']["monthlyPlays"].extend([-1] * missedMonths)
            orgData['orgStats']["monthlyPlays24h"].extend([-1] * missedMonths)
            orgData['orgStats']["monthlyUniquePlays24h"].extend([-1] * missedMonths)
            orgData['orgStats']["monthlyTimestamps"].extend([None] * missedMonths)

        filtered = [num for num in orgData['orgStats']["dailyPlayerCounts"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        orgData['orgStats']["monthlyPlayerCounts"].append(value)

        filtered = [num for num in orgData['orgStats']["dailyPlays"] if num != -1]
        if (len(filtered) >= 1): value = filtered[-1]
        else: value = -1
        orgData['orgStats']["monthlyPlays"].append(value)

        filtered = [num for num in orgData['orgStats']["dailyPlays24h"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        orgData['orgStats']["monthlyPlays24h"].append(value)

        filtered = [num for num in orgData['orgStats']["dailyUniquePlays24h"] if num != -1]
        if (len(filtered) >= 1): value = sum(filtered) / len(filtered)
        else: value = -1
        orgData['orgStats']["monthlyUniquePlays24h"].append(value)

        filtered = [t for t in orgData['orgStats']["dailyTimestamps"] if t is not None]
        orgData['orgStats']["monthlyTimestamps"].append(filtered[-1] if len(filtered) >= 1 else None)

        del orgData['orgStats']["monthlyPlayerCounts"][:months]
        del orgData['orgStats']["monthlyPlays"][:months]
        del orgData['orgStats']["monthlyPlays24h"][:months]
        del orgData['orgStats']["monthlyUniquePlays24h"][:months]
        del orgData['orgStats']["monthlyTimestamps"][:months]

        update_organization_stats(org_id, orgData['orgStats'])

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