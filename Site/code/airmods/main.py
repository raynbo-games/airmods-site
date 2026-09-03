from flask import Blueprint, render_template, url_for, abort
from Site.code.auth.main import login_required, get_user
from Site.code.database.main import get_matching_row
from Site.code.database.cdn import get_image_cdn_url
from Site.code.settings.database import get_games_for_user, is_organization_linked_to_user

bp = Blueprint('airmods', __name__, url_prefix='/airmods')

@bp.context_processor
def inject_airmods_global():
    return dict(title="Airmods")

@bp.route('')
def root():
    return render_template('airmods/index.html')

@bp.route('/games')
@login_required()
def games():
    game_rows = get_games_for_user(get_user()["id"])
    game_list = [{
        "id": g["id"],
        "name": g["name"],
        "image_url": get_image_cdn_url("airspy", g["iconImageId"]),
        "support_url": url_for("airmods.game_support", game_id=g["id"])
    } for g in game_rows]
    return render_template('airmods/games.html', games=game_list)

@bp.route('/games/<game_id>/support')
@login_required()
def game_support(game_id):
    game_data = get_matching_row("game", {"id": game_id})
    if not game_data or not is_organization_linked_to_user(get_user()["id"], game_data["organizationId"]):
        abort(403)
    return render_template('airmods/support.html', game_data=dict(game_data))
