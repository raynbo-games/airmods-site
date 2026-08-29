from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from Site.code.airspy.utility import get_search_items, get_dashboard_data, get_game_list, get_organization_list
from Site.code.database.cdn import get_image_cdn_url
from Site.code.database.main import get_matching_row

bp = Blueprint('airspy', __name__, url_prefix='/airspy')

@bp.context_processor
def inject_airspy_global():
    return dict(title="Airspy")

@bp.route('/')
def root():
    return render_template(
        'airspy/index.html',
        games=get_game_list(),
        orgs=get_organization_list()
    )

@bp.route('/games')
def games():
    return render_template(
        'airspy/games/index.html',
        games=get_game_list()
    )

@bp.route('/games/<game_id>')
def game(game_id):
    gameData = get_matching_row("game", {"id": game_id})
    data = get_dashboard_data(gameData["gameStats"])
    
    return render_template(
        'airspy/games/view.html',
        chart_url=url_for("airspy.game_chart", game_id=game_id),
        ath_data=data["ath_data"],
        game_data=dict(gameData),
        image_url=get_image_cdn_url("airspy", gameData["iconImageId"])
    )

@bp.route('/games/chart/<game_id>')
def game_chart(game_id):
    gameData = get_matching_row("game", {"id": game_id})
    data = get_dashboard_data(gameData["gameStats"])
    return jsonify(dict(data["chart_data"]))

@bp.route('/games/n/<game_name>')
def game_by_name(game_name):
    game = get_matching_row("game", {"name": game_name})
    return redirect(url_for("airspy.game", game_id=game["id"]))

@bp.route('/organizations')
def organizations():
    return render_template(
        'airspy/organizations/index.html',
        orgs=get_organization_list()
    )

@bp.route('/organizations/<organization_id>')
def organization(organization_id):
    orgData = get_matching_row("organization", {"id": organization_id})
    data = get_dashboard_data(orgData["orgStats"])
    
    return render_template(
        'airspy/organizations/view.html',
        chart_url=url_for("airspy.organization_chart", organization_id=organization_id),
        ath_data=data["ath_data"],
        org_data=dict(orgData),
        image_url=get_image_cdn_url("airspy", orgData["iconImageId"])
    )

@bp.route('/organizations/chart/<organization_id>')
def organization_chart(organization_id):
    orgData = get_matching_row("organization", {"id": organization_id})
    data = get_dashboard_data(orgData["orgStats"])
    return jsonify(dict(data["chart_data"]))

@bp.route('/organizations/n/<organization_name>')
def organization_by_name(organization_name):
    org = get_matching_row("organization", {"name": organization_name})
    return redirect(url_for("airspy.organization", organization_id=org["id"]))

@bp.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    current_app.logger.info(query)
    search_items = get_search_items()
    current_app.logger.info(search_items)
    
    if not query:
        return jsonify([])

    matches = [item for item in search_items if query in item["title"].lower()]
    current_app.logger.info(matches)
    return jsonify(matches)