from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, abort
from Site.code.airspy.utility import get_search_items, get_dashboard_data, get_game_list, get_organization_list, get_organization_games, get_visible_game_rows, get_global_stats
from Site.code.airspy.compile import get_global_stats_data
from Site.code.database.cdn import get_image_cdn_url
from Site.code.database.main import get_matching_row

bp = Blueprint('airspy', __name__, url_prefix='/airspy')

@bp.context_processor
def inject_airspy_global():
    return dict(title="Airspy")

@bp.route('')
def root():
    game_rows = get_visible_game_rows()
    global_stats_data = get_global_stats_data()
    return render_template(
        'airspy/index.html',
        games=get_game_list(game_rows),
        orgs=get_organization_list(),
        global_stats=get_global_stats(game_rows, global_stats_data),
        ath_data=get_dashboard_data(global_stats_data)["ath_data"],
        chart_url=url_for("airspy.global_chart")
    )

@bp.route('/chart')
def global_chart():
    data = get_dashboard_data(get_global_stats_data())
    return jsonify(dict(data["chart_data"]))

@bp.route('/games')
def games():
    return render_template(
        'airspy/games/index.html',
        games=get_game_list()
    )

@bp.route('/games/<game_id>')
def game(game_id):
    game_data = get_matching_row("game", {"id": game_id})
    if not game_data or game_data["hiddenFromAirspy"]:
        abort(404)
    data = get_dashboard_data(game_data["gameStats"])

    return render_template(
        'airspy/games/view.html',
        chart_url=url_for("airspy.game_chart", game_id=game_id),
        ath_data=data["ath_data"],
        game_data=dict(game_data),
        image_url=get_image_cdn_url("airspy", game_data["iconImageId"])
    )

@bp.route('/games/chart/<game_id>')
def game_chart(game_id):
    game_data = get_matching_row("game", {"id": game_id})
    if not game_data or game_data["hiddenFromAirspy"]:
        abort(404)
    data = get_dashboard_data(game_data["gameStats"])
    return jsonify(dict(data["chart_data"]))

@bp.route('/games/n/<game_name>')
def game_by_name(game_name):
    game = get_matching_row("game", {"name": game_name})
    if not game or game["hiddenFromAirspy"]:
        abort(404)
    return redirect(url_for("airspy.game", game_id=game["id"]))

@bp.route('/organizations')
def organizations():
    return render_template(
        'airspy/organizations/index.html',
        orgs=get_organization_list()
    )

@bp.route('/organizations/<organization_id>')
def organization(organization_id):
    org_data = get_matching_row("organization", {"id": organization_id})
    if not org_data or org_data["hiddenFromAirspy"]:
        abort(404)
    data = get_dashboard_data(org_data["orgStats"])

    return render_template(
        'airspy/organizations/view.html',
        chart_url=url_for("airspy.organization_chart", organization_id=organization_id),
        ath_data=data["ath_data"],
        org_data=dict(org_data),
        games=get_organization_games(organization_id),
        image_url=get_image_cdn_url("airspy", org_data["iconImageId"])
    )

@bp.route('/organizations/chart/<organization_id>')
def organization_chart(organization_id):
    org_data = get_matching_row("organization", {"id": organization_id})
    if not org_data or org_data["hiddenFromAirspy"]:
        abort(404)
    data = get_dashboard_data(org_data["orgStats"])
    return jsonify(dict(data["chart_data"]))

@bp.route('/organizations/n/<organization_name>')
def organization_by_name(organization_name):
    org = get_matching_row("organization", {"name": organization_name})
    if not org or org["hiddenFromAirspy"]:
        abort(404)
    return redirect(url_for("airspy.organization", organization_id=org["id"]))

@bp.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])

    matches = [item for item in get_search_items() if query in item["title"].lower()]
    return jsonify(matches)
