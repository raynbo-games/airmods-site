from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from Site.code.airspy.api import bp as api_bp, get_image, get_search_items, get_dashboard_data
from Site.code.airspy.database import get_matching_row

bp = Blueprint('airspy', __name__, url_prefix='/airspy')

@bp.route('/')
def airspy():
    return render_template(
        'airspy/index.html',
        title="Airspy",
        year=datetime.now().year,
    )

@bp.route('/search')
def search():
    search_items = get_search_items()
    query = request.args.get('q', '').strip()
    if query:
        results = [item for item in search_items if query.lower() in item.lower()]
    else:
        results = search_items

    return render_template(
        'airspy/search.html',
        title="Airspy",
        results=results,
        query=query,
        year=datetime.now().year,
    )

@bp.route('/games')
def games():
    return render_template(
        'airspy/games/index.html',
        title="Airspy",
        year=datetime.now().year,
    )

@bp.route('/games/<game_id>')
def game(game_id):
    gameData = get_matching_row("game", {"id": game_id})
    data = get_dashboard_data(gameData["gameStats"])
    
    return render_template(
        'airspy/games/view.html',
        title="Airspy",
        year=datetime.now().year,
        chart_data=data["chart_data"],
        ath_data=data["ath_data"],
        game_data=dict(gameData),
        game_image=get_image(gameData["iconImageId"])
    )

@bp.route('/games/n/<game_name>')
def game_by_name(game_name):
    game = get_matching_row("game", {"name": game_name})
    return redirect(url_for("airspy.game", game_id=game["id"]))

@bp.route('/organizations')
def organizations():
    return render_template(
        'airspy/organizations/index.html',
        title="Airspy",
        year=datetime.now().year,
    )

@bp.route('/organizations/<organization_id>')
def organization(organization_id):
    orgData = get_matching_row("organization", {"id": organization_id})
    data = get_dashboard_data(orgData["orgStats"])
    
    return render_template(
        'airspy/organizations/view.html',
        title="Airspy",
        year=datetime.now().year,
        chart_data=data["chart_data"],
        ath_data=data["ath_data"],
        org_data=dict(orgData),
        org_image=get_image(orgData["iconImageId"])
    )

@bp.route('/organizations/n/<organization_name>')
def organization_by_name(organization_name):
    org = get_matching_row("organization", {"name": organization_name})
    return redirect(url_for("airspy.organization", organization_id=org["id"]))

bp.register_blueprint(api_bp)