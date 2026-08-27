from flask import Blueprint, request, jsonify, current_app, url_for
from Site.code.airspy.airship_urls import request_image
from Site.code.airspy.database import get_matching_row, get_property_value
from Site.code.config import STORED_TICKS, STORED_DAILY_TICKS, STORED_MONTHLY_TICKS
import base64

def get_search_items():
    items = []
    game_names = get_property_value("game", "name")
    for name in game_names:
        items.append({
            "title": f"Game: {name}",
            "url": url_for("airspy.game_by_name", game_name=name)
        })
    org_names = get_property_value("organization", "name")
    for name in org_names:
        items.append({
            "title": f"Org:  {name}",
            "url": url_for("airspy.organization_by_name", organization_name=name)
        })
    return items

def get_dashboard_data(stats):
    chart_data = {
        "day": {
            "labels": [f"Tick #{STORED_TICKS - i}" for i in range(1, STORED_TICKS + 1)],
            "graphs": [
                {"title": "Player Count", "unit": " players", "values": stats["playerCounts"]},
                {"title": "Plays", "unit": " plays", "values": stats["plays"]},
                {"title": "Plays 24h", "unit": " plays 24h", "values": stats["plays24h"]},
                {"title": "Unique Plays 24h", "unit": "unique plays 24h", "values": stats["uniquePlays24h"]}
            ]
        },
        "month": {
            "labels": [f"Tick #{STORED_DAILY_TICKS - i}" for i in range(1, STORED_DAILY_TICKS + 1)],
            "graphs": [
                {"title": "Player Count", "unit": " players", "values": stats["dailyPlayerCounts"]},
                {"title": "Plays", "unit": " plays", "values": stats["dailyPlays"]},
                {"title": "Plays 24h", "unit": " plays 24h", "values": stats["dailyPlays24h"]},
                {"title": "Unique Plays 24h", "unit": "unique plays 24h", "values": stats["dailyUniquePlays24h"]}
            ]
        },
        "year": {
            "labels": [f"Tick #{STORED_MONTHLY_TICKS - i}" for i in range(1, STORED_MONTHLY_TICKS + 1)],
            "graphs": [
                {"title": "Player Count", "unit": " players", "values": stats["monthlyPlayerCounts"]},
                {"title": "Plays", "unit": " plays", "values": stats["monthlyPlays"]},
                {"title": "Plays 24h", "unit": " plays 24h", "values": stats["monthlyPlays24h"]},
                {"title": "Unique Plays 24h", "unit": "unique plays 24h", "values": stats["monthlyUniquePlays24h"]}
            ]
        }
    }
    ath_data = {
        "playerCount": stats["athPlayerCount"],
        "plays24h": stats["athPlays24h"],
        "uniquePlays24h": stats["athUniquePlays24h"],
    }
    return {
        "chart_data": chart_data,
        "ath_data": ath_data
    }


def get_image(image_id):
    buffer = request_image(image_id)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')