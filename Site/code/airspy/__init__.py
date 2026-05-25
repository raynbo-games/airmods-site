import json
import os
from flask import Blueprint, current_app, jsonify, render_template
from datetime import datetime
from Site.code.airspy.tracker import GAMES_PATH, startTrackerThread

def Start(app):
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        startTrackerThread()

bp = Blueprint('airspy', __name__, url_prefix='/airspy')

@bp.route('')
def main():
    """Renders the home page."""
    return render_template(
        'airspy/index.html',
        title="Airspy",
        year=datetime.now().year,
    )

@bp.route('/api')
def api():
    return render_template(
        'airspy/api.html',
        title="Airspy API",
        year=datetime.now().year,
    )

@bp.route('/api/games')
def games():
    gameIds = []
    for filename in os.listdir(os.path.join(current_app.instance_path, GAMES_PATH)):
        if filename.endswith('.json'):
            gameId = os.path.splitext(filename)[0]
            gameIds.append(gameId)
    return jsonify(gameIds)

@bp.route('/api/games/<gameId>')
def gameById(gameId):
    filePath = os.path.join(current_app.instance_path, GAMES_PATH, f"{gameId}.json")
    
    if not os.path.exists(filePath):
        return jsonify({"error": f"Game with ID '{gameId}' not found"}), 404
        
    with open(filePath, 'r') as f:
        try:
            gameData = json.load(f)
            return jsonify(gameData)
        except json.JSONDecodeError:
            return jsonify({"error": "Failed to parse game data"}), 500