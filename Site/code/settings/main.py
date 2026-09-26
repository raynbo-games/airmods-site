from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify, send_file
from Site.code.auth.main import login_required, get_user
from Site.code.auth.database import update_username
from Site.code.admin.database import add_audit_log
from Site.code.database.main import get_matching_row
from Site.code.database.cdn import get_image_cdn_url, upload_to_spaces
from Site.code.airspy.airship_urls import request_game_id, request_image, get_image_url
from Site.code.airspy.database import update_game, update_organization
from Site.code.settings.database import (
    get_linked_organizations, is_organization_linked_to_user,
    link_organization, unlink_organization, set_game_hidden,
    set_organization_hidden, verify_username_change
)
from Site.code.settings.tokens import create_link_token, read_link_token
from Site.code.settings.qr import generate_qr_png, decode_qr
from Site.code.config import AIRSPY_ORG_LINK_TOKEN_MAX_AGE

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.context_processor
def inject_settings_global():
    return dict(title="Settings")

@bp.route('')
@login_required()
def root():
    return redirect(url_for('settings.profile'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required()
def profile():
    user = get_user()
    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        verify = verify_username_change(user, username)
        if not verify["valid"]:
            error = verify["message"]
        else:
            update_username(user["id"], username)
            return redirect(url_for('settings.profile'))

    return render_template('settings/profile.html', user=user, error=error)

@bp.route('/profile/verify')
@login_required()
def profile_verify():
    username = request.args.get('username', '')
    return jsonify(verify_username_change(get_user(), username))

@bp.route('/connections')
@login_required()
def connections():
    orgs = get_linked_organizations(get_user()["id"])
    organizations = [{
        "id": org["id"],
        "name": org["name"],
        "image_url": get_image_cdn_url("airspy", org["iconImageId"]),
        "url": url_for("settings.connection_detail", organization_id=org["id"]),
        "hidden": org["hiddenFromAirspy"]
    } for org in orgs]
    return render_template('settings/connections.html', organizations=organizations)

@bp.route('/connections/link', methods=['GET', 'POST'])
@login_required()
def connection_link():
    error = None

    if request.method == 'POST':
        game_id = request.form.get('game_id', '').strip()
        raw_data = request_game_id(game_id, liveStats=True) if game_id else None
        if not raw_data:
            error = "No game found with that ID. Double check it on your Airship dashboard."
        else:
            update_game(raw_data)
            upload_to_spaces("airspy", raw_data["game"]["iconImageId"], get_image_url(raw_data["game"]["iconImageId"]))
            org = raw_data["game"]["organization"]
            update_organization(org)
            upload_to_spaces("airspy", org["iconImageId"], get_image_url(org["iconImageId"]))
            token = create_link_token(get_user()["id"], org["id"], game_id)
            return redirect(url_for('settings.connection_link_verify', organization_id=org["id"], token=token))

    return render_template('settings/link.html', error=error)

@bp.route('/connections/link/<organization_id>/verify')
@login_required()
def connection_link_verify(organization_id):
    token = request.args.get('token', '')
    payload, error = read_link_token(token)
    if error or payload["userId"] != get_user()["id"] or payload["organizationId"] != organization_id:
        abort(400, "Invalid or expired link request")

    org = get_matching_row("organization", {"id": organization_id})
    if not org:
        abort(404)

    return render_template(
        'settings/verify.html',
        organization=dict(org),
        token=token,
        max_age=AIRSPY_ORG_LINK_TOKEN_MAX_AGE,
        confirm_url=url_for('settings.connection_link_confirm', organization_id=organization_id),
        qr_url=url_for('settings.connection_link_qr', token=token),
        connections_url=url_for('settings.connections')
    )

@bp.route('/connections/link/qr/<token>')
@login_required()
def connection_link_qr(token):
    payload, error = read_link_token(token)
    if error:
        abort(400, "Invalid or expired token")
    if payload["userId"] != get_user()["id"]:
        abort(403)
    return send_file(generate_qr_png(token), mimetype='image/png')

@bp.route('/connections/link/<organization_id>/confirm', methods=['POST'])
@login_required()
def connection_link_confirm(organization_id):
    token = request.form.get('token', '')
    payload, error = read_link_token(token)
    if error == "expired":
        return jsonify({"status": "expired"})
    if error == "invalid":
        abort(400, "Invalid token")
    if payload["userId"] != get_user()["id"] or payload["organizationId"] != organization_id:
        abort(400, "Token does not match this request")

    raw_data = request_game_id(payload["gameId"])
    if raw_data is None:
        return jsonify({"status": "pending"})

    org = raw_data["game"]["organization"]
    if org["id"] != organization_id:
        abort(400, "Game no longer belongs to this organization")

    image_buffer = request_image(org["iconImageId"])
    if image_buffer is None:
        return jsonify({"status": "pending"})

    decoded = decode_qr(image_buffer.getvalue())
    if decoded != token:
        return jsonify({"status": "pending"})

    # org["iconImageId"] is the QR code itself right now (that's how we just verified
    # ownership) - don't let it overwrite the org's real icon on the site.
    existing_org = get_matching_row("organization", {"id": organization_id})
    org["iconImageId"] = existing_org["iconImageId"] if existing_org else org["iconImageId"]
    update_organization(org)
    link_organization(get_user()["id"], organization_id)
    add_audit_log(
        get_user(), None, "link_organization",
        "Self-service Airship organization link",
        details=f"Linked organization {org['name']} ({org['id']})"
    )
    return jsonify({"status": "success", "redirect": url_for("settings.connections")})

@bp.route('/connections/<organization_id>/unlink', methods=['POST'])
@login_required()
def connection_unlink(organization_id):
    if not is_organization_linked_to_user(get_user()["id"], organization_id):
        abort(403)

    org = get_matching_row("organization", {"id": organization_id})
    unlink_organization(get_user()["id"], organization_id)
    add_audit_log(
        get_user(), None, "unlink_organization",
        "Self-service Airship organization unlink",
        details=f"Unlinked organization {org['name'] if org else organization_id} ({organization_id})"
    )
    return redirect(url_for('settings.connections'))

@bp.route('/connections/<organization_id>/games/add', methods=['POST'])
@login_required()
def connection_add_game(organization_id):
    if not is_organization_linked_to_user(get_user()["id"], organization_id):
        abort(403)

    game_id = request.form.get('game_id', '').strip()
    raw_data = request_game_id(game_id, liveStats=True) if game_id else None
    if not raw_data or raw_data["game"]["organization"]["id"] != organization_id:
        abort(400, "That game ID doesn't belong to this organization.")

    update_game(raw_data)
    upload_to_spaces("airspy", raw_data["game"]["iconImageId"], get_image_url(raw_data["game"]["iconImageId"]))
    add_audit_log(
        get_user(), None, "link_game",
        "Self-service Airship game link",
        details=f"Linked game {raw_data['game']['name']} ({game_id}) to organization {organization_id}"
    )
    return redirect(url_for('settings.connection_detail', organization_id=organization_id))

@bp.route('/connections/<organization_id>', methods=['GET', 'POST'])
@login_required()
def connection_detail(organization_id):
    if not is_organization_linked_to_user(get_user()["id"], organization_id):
        abort(403)

    org = get_matching_row("organization", {"id": organization_id})
    if not org:
        abort(404)

    if request.method == 'POST':
        games = get_matching_row("game", {"organizationId": organization_id}, multiple=True)
        game_ids = {game_row["id"] for game_row in games}
        org_visible_requested = request.form.get('org_visible') == 'on'

        # Hiding the organization hides all of its games too, regardless of
        # what was checked - there's no "hidden org, visible game" state.
        visible_ids = (set(request.form.getlist('visible')) & game_ids) if org_visible_requested else set()

        for game_row in games:
            set_game_hidden(game_row["id"], organization_id, game_row["id"] not in visible_ids)
        set_organization_hidden(organization_id, not org_visible_requested)
        return redirect(url_for('settings.connection_detail', organization_id=organization_id))

    games = get_matching_row("game", {"organizationId": organization_id}, multiple=True)
    game_list = [{
        "id": g["id"],
        "name": g["name"],
        "image_url": get_image_cdn_url("airspy", g["iconImageId"]),
        "hidden": g["hiddenFromAirspy"]
    } for g in games]

    return render_template(
        'settings/connection_detail.html',
        organization=dict(org),
        image_url=get_image_cdn_url("airspy", org["iconImageId"]),
        games=game_list
    )
