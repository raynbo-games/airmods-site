from datetime import timezone
from flask import Blueprint, render_template, request, redirect, url_for, abort
from Site.code.auth.main import login_required, get_user
from Site.code.admin.database import add_audit_log
from Site.code.database.main import get_matching_row
from Site.code.database.cdn import get_image_cdn_url
from Site.code.settings.database import get_games_for_user, is_organization_linked_to_user
from Site.code.airmods.database import create_api_token, get_api_tokens_for_game, revoke_api_token

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

def require_owned_game(game_id):
    game_data = get_matching_row("game", {"id": game_id})
    if not game_data or not is_organization_linked_to_user(get_user()["id"], game_data["organizationId"]):
        abort(403)
    return game_data

def get_token_list(game_id):
    tokens = get_api_tokens_for_game(game_id)
    token_list = []
    for token in tokens:
        token = dict(token)
        token["createdAtIso"] = token["createdAt"].replace(tzinfo=timezone.utc).isoformat()
        token["lastUsedAtIso"] = token["lastUsedAt"].replace(tzinfo=timezone.utc).isoformat() if token["lastUsedAt"] else None
        token_list.append(token)
    return token_list

@bp.route('/games/<game_id>/support')
@login_required()
def game_support(game_id):
    game_data = require_owned_game(game_id)
    return render_template('airmods/support.html', game_data=dict(game_data), tokens=get_token_list(game_id))

@bp.route('/games/<game_id>/support/tokens', methods=['POST'])
@login_required()
def create_token(game_id):
    game_data = require_owned_game(game_id)

    name = request.form.get('name', '').strip() or "Unnamed Token"
    token = create_api_token(game_id, get_user()["id"], name)
    add_audit_log(
        get_user(), None, "create_api_token",
        "Self-service Airmods API token creation",
        details=f"Created token \"{name}\" for game {game_data['name']} ({game_id})"
    )
    return render_template('airmods/support.html', game_data=dict(game_data), tokens=get_token_list(game_id), new_token=token)

@bp.route('/games/<game_id>/support/tokens/<int:token_id>/revoke', methods=['POST'])
@login_required()
def revoke_token(game_id, token_id):
    game_data = require_owned_game(game_id)

    revoke_api_token(token_id, game_id)
    add_audit_log(
        get_user(), None, "revoke_api_token",
        "Self-service Airmods API token revocation",
        details=f"Revoked token {token_id} for game {game_data['name']} ({game_id})"
    )
    return redirect(url_for('airmods.game_support', game_id=game_id))
