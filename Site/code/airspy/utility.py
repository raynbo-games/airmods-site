from flask import url_for
from Site.code.config import AIRSPY_UPDATE_TIMEOUT, AIRSPY_CHART_BUCKET_MINUTES
from Site.code.database.cdn import get_image_cdn_url
from Site.code.database.main import get_matching_row

def get_search_items():
    items = []
    game_rows = get_matching_row("game", {"hiddenFromAirspy": False}, multiple=True)
    for row in game_rows:
        items.append({
            "title": f"Game: {row['name']}",
            "url": url_for("airspy.game_by_name", game_name=row["name"])
        })
    org_rows = get_matching_row("organization", {"hiddenFromAirspy": False}, multiple=True)
    for row in org_rows:
        items.append({
            "title": f"Org:  {row['name']}",
            "url": url_for("airspy.organization_by_name", organization_name=row["name"])
        })
    return items

def bucket_series(values, timestamps, bucket_size, mode="last"):
    """Downsample a tick-resolution series into fixed-size buckets, anchored to the
    most recent tick so the latest value/timestamp is always represented."""
    n = len(values)
    if bucket_size <= 1 or n == 0:
        return values, timestamps

    bucketed_values = []
    bucketed_labels = []

    end = n
    while end > 0:
        start = max(0, end - bucket_size)
        value_window = values[start:end]
        timestamp_window = timestamps[start:end]

        filtered_values = [v for v in value_window if v != -1]
        filtered_timestamps = [t for t in timestamp_window if t]

        if mode == "average":
            value = sum(filtered_values) / len(filtered_values) if filtered_values else -1
        else:
            value = filtered_values[-1] if filtered_values else -1

        bucketed_values.append(value)
        bucketed_labels.append(filtered_timestamps[-1] if filtered_timestamps else None)

        end = start

    bucketed_values.reverse()
    bucketed_labels.reverse()
    return bucketed_values, bucketed_labels

def get_dashboard_data(stats):
    """Build chart-ready series (day/month/year) plus all-time-high data for a game or organization."""
    ticks_per_bucket = max(1, round(AIRSPY_CHART_BUCKET_MINUTES / AIRSPY_UPDATE_TIMEOUT))

    day_player_counts, day_labels = bucket_series(stats["playerCounts"], stats["timestamps"], ticks_per_bucket, mode="average")
    day_plays, _ = bucket_series(stats["plays"], stats["timestamps"], ticks_per_bucket, mode="last")
    day_plays24h, _ = bucket_series(stats["plays24h"], stats["timestamps"], ticks_per_bucket, mode="last")
    day_unique_plays24h, _ = bucket_series(stats["uniquePlays24h"], stats["timestamps"], ticks_per_bucket, mode="last")

    chart_data = {
        "day": {
            "labels": day_labels,
            "graphs": [
                {"title": "Player Count", "unit": " players", "values": day_player_counts},
                {"title": "Plays", "unit": " plays", "values": day_plays},
                {"title": "Plays 24h", "unit": " plays 24h", "values": day_plays24h},
                {"title": "Unique Plays 24h", "unit": "unique plays 24h", "values": day_unique_plays24h}
            ]
        },
        "month": {
            "labels": stats["dailyTimestamps"],
            "graphs": [
                {"title": "Player Count", "unit": " players", "values": stats["dailyPlayerCounts"]},
                {"title": "Plays", "unit": " plays", "values": stats["dailyPlays"]},
                {"title": "Plays 24h", "unit": " plays 24h", "values": stats["dailyPlays24h"]},
                {"title": "Unique Plays 24h", "unit": "unique plays 24h", "values": stats["dailyUniquePlays24h"]}
            ]
        },
        "year": {
            "labels": stats["monthlyTimestamps"],
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

def get_game_list():
    game_data = get_matching_row("game", {"hiddenFromAirspy": False}, multiple=True)
    games = []
    for data in game_data:
        games.append({
            "name": data["name"],
            "url": url_for("airspy.game", game_id=data["id"]),
            "image_url": get_image_cdn_url("airspy", data["iconImageId"])
        })
    return games

def get_organization_games(organization_id):
    game_data = get_matching_row("game", {"organizationId": organization_id, "hiddenFromAirspy": False}, multiple=True)
    games = []
    for data in game_data:
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
        organizations.append({
            "name": data["name"],
            "url": url_for("airspy.organization", organization_id=data["id"]),
            "image_url": get_image_cdn_url("airspy", data["iconImageId"])
        })
    return organizations