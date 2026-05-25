from asyncio import tasks
from logging import warning
import math
import threading
import time
from datetime import datetime
import requests
import json
import os
from flask import current_app

GAMES_URL = "https://api.airship.gg/content/games"
GAMES_PATH = os.path.abspath(os.path.join(__file__, "../../../bin/airspy/games/"))

def serializeGameData(gameData, minute):
    gameInfo = {
        "id": gameData["id"],
        "slug": gameData["slug"],
        "name": gameData["name"],
        "description": gameData["description"],
        "iconImageId": gameData["iconImageId"],
        "owner": {
            "id": gameData["organization"]["id"],
            "name": gameData["organization"]["name"],
        },
        "visibility": gameData["visibility"],
        "lastVersionUpdate": gameData["lastVersionUpdate"],
        "platforms": gameData["platforms"],
    }
    gameStats = {
        "minute": minute,
        "plays": gameData["plays"],
        "plays24h": gameData["plays24h"],
        "uniquePlays24h": gameData["uniquePlays24h"],
        "players": gameData["liveStats"]["playerCount"],
    }

    filePath = os.path.join(GAMES_PATH, f'{gameInfo["id"]}.json')

    if os.path.exists(filePath):
        with open(filePath, 'r') as f:
            gameData = json.load(f)
    else:
        gameData = {
            "info": {},
            "topStats": {
                "plays": 0,
                "plays24h": 0,
                "uniquePlays24h": 0,
                "players": 0,
            },
            "firstTracked": gameStats["minute"],
            "lastTracked": gameStats["minute"],
            "stats": [],
        }

    gameData["info"] = gameInfo
    gameData["topStats"]["plays"] = max(gameData["topStats"]["plays"], gameStats["plays"])
    gameData["topStats"]["plays24h"] = max(gameData["topStats"]["plays24h"], gameStats["plays24h"])
    gameData["topStats"]["uniquePlays24h"] = max(gameData["topStats"]["uniquePlays24h"], gameStats["uniquePlays24h"])
    gameData["topStats"]["players"] = max(gameData["topStats"]["players"], gameStats["players"])
    gameData["lastTracked"] = gameStats["minute"]
    gameData["stats"].append(gameStats)
    

    with open(filePath, 'w') as f:
        json.dump(gameData, f)


def startTracker():
    while True:
        minute = math.floor(datetime.now().timestamp() / 60)
        try:
            response = requests.get(GAMES_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                finished = []
                for gameData in data["popular"]:
                    if gameData["id"] in finished:
                        continue
                    serializeGameData(gameData, minute)
                    finished.append(gameData["id"])
                for gameData in data["featured"]:
                    if gameData["id"] in finished:
                        continue
                    serializeGameData(gameData, minute)
                    finished.append(gameData["id"])
                for gameData in data["recentlyUpdated"]:
                    if gameData["id"] in finished:
                        continue
                    serializeGameData(gameData, minute)
                    finished.append(gameData["id"])
            else:
                warning(f"[{minute}] Received unexpected status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            warning(f"[{minute}] Error connecting to API: {e}")

        time.sleep(60)


def startTrackerThread():
    trackerThread = threading.Thread(target=startTracker, daemon=True)
    trackerThread.start()