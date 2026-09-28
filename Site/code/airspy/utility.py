from datetime import datetime
from flask import url_for
from Site.code.airspy.database import get_airspy_settings
from Site.code.database.cdn import get_image_cdn_url
from Site.code.database.main import get_matching_row

def get_games_updated_after_cutoff():
    """The admin-configured cutoff (a datetime, or None) below which games are
    hidden from the public games list, organization pages, and search."""
    value = get_airspy_settings().get("gamesUpdatedAfter")
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None

def get_search_items():
    cutoff = get_games_updated_after_cutoff()
    items = []
    game_rows = get_matching_row("game", {"hiddenFromAirspy": False}, multiple=True)
    for row in game_rows:
        if cutoff and row["lastVersionUpdate"] < cutoff:
            continue
        items.append({
            "title": f"Game: {row['name']}",
            "url": url_for("airspy.game_by_name", game_name=row["name"])
        })
    org_rows = get_matching_row("organization", {"hiddenFromAirspy": False}, multiple=True)
    for row in org_rows:
        if not get_organization_games(row["id"]):
            continue
        items.append({
            "title": f"Org:  {row['name']}",
            "url": url_for("airspy.organization_by_name", organization_name=row["name"])
        })
    return items

def get_dashboard_data(stats):
    """Build chart-ready series (day/month/year) plus all-time-high data for a game or organization."""
    chart_data = {
        "day": {
            "labels": stats["timestamps"],
            "graphs": [
                {"title": "Player Count", "unit": " players", "values": stats["playerCounts"]},
                {"title": "Plays", "unit": " plays", "values": stats["plays"]},
                {"title": "Plays 24h", "unit": " plays 24h", "values": stats["plays24h"]},
                {"title": "Unique Plays 24h", "unit": "unique plays 24h", "values": stats["uniquePlays24h"]}
            ]
        },
        "month": {
            "labels": stats["dailyTimestamps"],
            "graphs": [
                {"title": "Average Player Count", "unit": " players", "values": stats["dailyPlayerCounts"]},
                {"title": "Plays", "unit": " plays", "values": stats["dailyPlays"]},
                {"title": "Plays 24h", "unit": " plays 24h", "values": stats["dailyPlays24h"]},
                {"title": "Unique Plays 24h", "unit": "unique plays 24h", "values": stats["dailyUniquePlays24h"]}
            ]
        },
        "year": {
            "labels": stats["monthlyTimestamps"],
            "graphs": [
                {"title": "Average Player Count", "unit": " players", "values": stats["monthlyPlayerCounts"]},
                {"title": "Plays", "unit": " plays", "values": stats["monthlyPlays"]},
                {"title": "Plays 24h", "unit": " plays 24h", "values": stats["monthlyPlays24h"]},
                {"title": "Unique Plays 24h", "unit": "unique plays 24h", "values": stats["monthlyUniquePlays24h"]}
            ]
        }
    }
    ath_data = {
        "playerCount": stats["athPlayerCount"],
        "playerCountAt": stats.get("athPlayerCountAt"),
        "plays24h": stats["athPlays24h"],
        "plays24hAt": stats.get("athPlays24hAt"),
        "uniquePlays24h": stats["athUniquePlays24h"],
        "uniquePlays24hAt": stats.get("athUniquePlays24hAt"),
    }
    return {
        "chart_data": chart_data,
        "ath_data": ath_data
    }

def get_visible_game_rows():
    cutoff = get_games_updated_after_cutoff()
    game_data = get_matching_row("game", {"hiddenFromAirspy": False}, multiple=True)
    return [data for data in game_data if not (cutoff and data["lastVersionUpdate"] < cutoff)]

def get_global_stats(game_rows, global_stats_data):
    """Latest reading of each compiled global series, plus favorites summed across visible games."""
    def latest(key):
        return next((value for value in reversed(global_stats_data[key]) if value != -1), 0)
    return {
        "playerCount": latest("playerCounts"),
        "plays": latest("plays"),
        "plays24h": latest("plays24h"),
        "uniquePlays24h": latest("uniquePlays24h"),
        "favorites": sum(data["favorites"] or 0 for data in game_rows),
    }

def get_game_list(game_rows=None):
    if game_rows is None:
        game_rows = get_visible_game_rows()
    games = []
    for data in game_rows:
        games.append({
            "name": data["name"],
            "url": url_for("airspy.game", game_id=data["id"]),
            "image_url": get_image_cdn_url("airspy", data["iconImageId"])
        })
    return games

def get_organization_games(organization_id):
    cutoff = get_games_updated_after_cutoff()
    game_data = get_matching_row("game", {"organizationId": organization_id, "hiddenFromAirspy": False}, multiple=True)
    games = []
    for data in game_data:
        if cutoff and data["lastVersionUpdate"] < cutoff:
            continue
        games.append({
            "name": data["name"],
            "url": url_for("airspy.game", game_id=data["id"]),
            "image_url": get_image_cdn_url("airspy", data["iconImageId"])
        })
    return games

def get_organization_list():
    organization_data = get_matching_row("organization", {"hiddenFromAirspy": False}, multiple=True)
    organizations = []
    for data in organization_data:
        if not get_organization_games(data["id"]):
            continue
        organizations.append({
            "name": data["name"],
            "url": url_for("airspy.organization", organization_id=data["id"]),
            "image_url": get_image_cdn_url("airspy", data["iconImageId"])
        })
    return organizations