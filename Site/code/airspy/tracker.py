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
            "stats": {
                "minutes": [],
                "hours": [],
                "days": [],
            },
        }

    gameData["info"] = gameInfo
    gameData["topStats"]["plays"] = max(gameData["topStats"]["plays"], gameStats["plays"])
    gameData["topStats"]["plays24h"] = max(gameData["topStats"]["plays24h"], gameStats["plays24h"])
    gameData["topStats"]["uniquePlays24h"] = max(gameData["topStats"]["uniquePlays24h"], gameStats["uniquePlays24h"])
    gameData["topStats"]["players"] = max(gameData["topStats"]["players"], gameStats["players"])
    gameData["lastTracked"] = gameStats["minute"]
    gameData["stats"]["minutes"].append(gameStats)

    while len(gameData["stats"]["minutes"]) > 60:
        del gameData["stats"]["minutes"][0]

    if minute % 60 == 0:
        hourStats = {
            "minute": gameData["stats"]["minutes"][-1]["minute"],
            "plays": gameData["stats"]["minutes"][-1]["plays"],
            "plays24h": gameData["stats"]["minutes"][-1]["plays24h"],
            "uniquePlays24h": gameData["stats"]["minutes"][-1]["uniquePlays24h"],
            "players": [],
        }

        for minuteData in gameData["stats"]["minutes"]:
            hourStats["players"].append(minuteData["players"])
        
        hourStats["players"] = round(sum(hourStats["players"]) / len(hourStats["players"]))
        gameData["stats"]["hours"].append(hourStats)

        while len(gameData["stats"]["hours"]) > 24:
            del gameData["stats"]["hours"][0]
    
    if minute % 1440 == 0:
        dayStats = {
            "minute": gameData["stats"]["minutes"][-1]["minute"],
            "plays": gameData["stats"]["minutes"][-1]["plays"],
            "plays24h": gameData["stats"]["minutes"][-1]["plays24h"],
            "uniquePlays24h": gameData["stats"]["minutes"][-1]["uniquePlays24h"],
            "players": [],
        }

        for hourData in gameData["stats"]["hours"]:
            dayStats["players"].append(hourData["players"])
        
        dayStats["players"] = round(sum(dayStats["players"]) / len(dayStats["players"]))
        gameData["stats"]["days"].append(dayStats)

        while len(gameData["stats"]["days"]) > 365:
            del gameData["stats"]["days"][0]

    with open(filePath, 'w') as f:
        json.dump(gameData, f)


def startTracker():
    while True:
        startTime = datetime.now().timestamp()
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
        elaspedTime = datetime.now().timestamp() - startTime
        time.sleep(60 - elaspedTime)


def startTrackerThread():
    trackerThread = threading.Thread(target=startTracker, daemon=True)
    trackerThread.start()