from datetime import timezone
from flask import Blueprint, render_template, redirect, url_for, request, abort, jsonify
from Site.code.auth.database import get_auth
from Site.code.auth.main import auth_required, login_required, get_user
from Site.code.community.webhook import send_discord_notification
from Site.code.roadmap.database import (
    STATUSES, create_roadmap, get_roadmaps, get_roadmap, rename_roadmap, delete_roadmap, touch_roadmap,
    get_boxes, get_box, create_box, update_box, update_box_position, delete_box,
    get_arrows, create_arrow, get_arrow, delete_arrow,
    get_box_score, get_user_box_vote, cast_box_vote,
    get_box_comments, get_box_comment_count, get_box_comment, create_box_comment, delete_box_comment,
    get_comment_score, has_user_upvoted_comment, toggle_comment_upvote
)

bp = Blueprint('roadmap', __name__, url_prefix='/roadmaps')

@bp.context_processor
def inject_roadmap_global():
    return dict(title="Roadmaps")

def can_edit():
    user = get_user()
    return bool(user and user["auth"] >= 3)

@bp.route('')
def index():
    roadmaps = get_roadmaps()
    if roadmaps:
        return redirect(url_for('roadmap.view', slug=roadmaps[0]["slug"]))
    return render_template('roadmap/index.html', roadmaps=roadmaps, can_edit=can_edit())

@bp.route('/new', methods=['GET', 'POST'])
@auth_required("DEVELOPER")
def new_roadmap():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            abort(400, "Name is required")
        _, slug = create_roadmap(name)
        return redirect(url_for('roadmap.view', slug=slug))
    return render_template('roadmap/new.html')

@bp.route('/<slug>')
def view(slug):
    roadmap = get_roadmap(slug)
    if not roadmap:
        abort(404)

    boxes = []
    for box in get_boxes(roadmap["id"]):
        box = dict(box)
        box["score"] = get_box_score(box["id"])
        box["commentCount"] = get_box_comment_count(box["id"])
        boxes.append(box)

    return render_template(
        'roadmap/view.html',
        roadmap=roadmap,
        roadmaps=get_roadmaps(),
        boxes=boxes,
        arrows=get_arrows(roadmap["id"]),
        statuses=STATUSES,
        can_edit=can_edit(),
    )

@bp.route('/<slug>/rename', methods=['POST'])
@auth_required("DEVELOPER")
def rename(slug):
    roadmap = get_roadmap(slug)
    if not roadmap:
        abort(404)

    name = request.form.get('name', '').strip()
    if not name:
        abort(400, "Name is required")

    rename_roadmap(roadmap["id"], name)
    return redirect(url_for('roadmap.view', slug=slug))

@bp.route('/<slug>/delete', methods=['POST'])
@auth_required("DEVELOPER")
def remove(slug):
    roadmap = get_roadmap(slug)
    if not roadmap:
        abort(404)

    delete_roadmap(roadmap["id"])
    return redirect(url_for('roadmap.index'))

@bp.route('/<slug>/boxes', methods=['POST'])
@auth_required("DEVELOPER")
def add_box(slug):
    roadmap = get_roadmap(slug)
    if not roadmap:
        abort(404)

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'planned')
    if not title or status not in STATUSES:
        abort(400, "Invalid step data")

    x = request.form.get('x', 40, type=int)
    y = request.form.get('y', 40, type=int)
    create_box(roadmap["id"], title, description, status, x, y)
    touch_roadmap(roadmap["id"])
    send_discord_notification("RoadmapNewStep", f"\U0001F5FA️ **{get_user()['username']}** added a new step to *{roadmap['name']}*: **{title}**")
    return redirect(url_for('roadmap.view', slug=slug))

@bp.route('/<slug>/boxes/<int:box_id>', methods=['POST'])
@auth_required("DEVELOPER")
def edit_box(slug, box_id):
    roadmap = get_roadmap(slug)
    box = get_box(box_id)
    if not roadmap or not box or box["roadmapId"] != roadmap["id"]:
        abort(404)

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'planned')
    if not title or status not in STATUSES:
        abort(400, "Invalid step data")

    update_box(box_id, title, description, status)
    touch_roadmap(roadmap["id"])
    send_discord_notification("RoadmapEditedStep", f"✏️ **{get_user()['username']}** edited step *{title}* on *{roadmap['name']}*")
    return redirect(url_for('roadmap.view', slug=slug))

@bp.route('/<slug>/boxes/<int:box_id>/position', methods=['POST'])
@auth_required("DEVELOPER")
def move_box(slug, box_id):
    roadmap = get_roadmap(slug)
    box = get_box(box_id)
    if not roadmap or not box or box["roadmapId"] != roadmap["id"]:
        abort(404)

    x = request.form.get('x', type=int)
    y = request.form.get('y', type=int)
    if x is None or y is None:
        abort(400, "Invalid position")

    update_box_position(box_id, max(0, x), max(0, y))
    touch_roadmap(roadmap["id"])
    return jsonify({"ok": True})

@bp.route('/<slug>/boxes/<int:box_id>/delete', methods=['POST'])
@auth_required("DEVELOPER")
def remove_box(slug, box_id):
    roadmap = get_roadmap(slug)
    box = get_box(box_id)
    if not roadmap or not box or box["roadmapId"] != roadmap["id"]:
        abort(404)

    delete_box(box_id)
    touch_roadmap(roadmap["id"])
    return redirect(url_for('roadmap.view', slug=slug))

@bp.route('/<slug>/arrows', methods=['POST'])
@auth_required("DEVELOPER")
def add_arrow(slug):
    roadmap = get_roadmap(slug)
    if not roadmap:
        abort(404)

    from_box_id = request.form.get('fromBoxId', type=int)
    to_box_id = request.form.get('toBoxId', type=int)
    from_box = get_box(from_box_id) if from_box_id else None
    to_box = get_box(to_box_id) if to_box_id else None

    if not from_box or not to_box or from_box["roadmapId"] != roadmap["id"] or to_box["roadmapId"] != roadmap["id"] or from_box_id == to_box_id:
        abort(400, "Invalid arrow")

    arrow_id = create_arrow(roadmap["id"], from_box_id, to_box_id)
    touch_roadmap(roadmap["id"])
    return jsonify({"ok": True, "id": arrow_id})

@bp.route('/<slug>/arrows/<int:arrow_id>/delete', methods=['POST'])
@auth_required("DEVELOPER")
def remove_arrow(slug, arrow_id):
    roadmap = get_roadmap(slug)
    arrow = get_arrow(arrow_id)
    if not roadmap or not arrow or arrow["roadmapId"] != roadmap["id"]:
        abort(404)

    delete_arrow(arrow_id)
    touch_roadmap(roadmap["id"])
    return jsonify({"ok": True})

def _get_roadmap_box_or_404(slug, box_id):
    roadmap = get_roadmap(slug)
    box = get_box(box_id)
    if not roadmap or not box or box["roadmapId"] != roadmap["id"]:
        abort(404)
    return roadmap, box

@bp.route('/<slug>/boxes/<int:box_id>/discussion')
def box_discussion(slug, box_id):
    """Fetch every comment including deleted ones so a reply's parent linkage never breaks on a
    parent invisible to this viewer; deleted comments' content is stripped out below instead."""
    _, box = _get_roadmap_box_or_404(slug, box_id)
    user = get_user()
    can_moderate = bool(user and user["auth"] >= get_auth("MODERATOR"))

    comments = []
    for comment in get_box_comments(box_id, include_deleted=True):
        comment = dict(comment)
        comment["createdAtIso"] = comment["createdAt"].replace(tzinfo=timezone.utc).isoformat()
        del comment["createdAt"]

        if comment["deleted"] and not can_moderate:
            comment["body"] = None
            comment["authorUsername"] = None
            comment["authorId"] = None
            comment["score"] = 0
            comment["userUpvoted"] = False
        else:
            comment["score"] = get_comment_score(comment["id"])
            comment["userUpvoted"] = bool(user and has_user_upvoted_comment(comment["id"], user["id"]))

        comments.append(comment)

    return jsonify({
        "score": get_box_score(box_id),
        "userVote": get_user_box_vote(box_id, user["id"]) if user else 0,
        "comments": comments,
        "userId": user["id"] if user else None,
        "canModerate": can_moderate,
    })

@bp.route('/<slug>/boxes/<int:box_id>/vote', methods=['POST'])
@login_required()
def vote_box(slug, box_id):
    _, box = _get_roadmap_box_or_404(slug, box_id)

    direction = request.form.get('direction')
    if direction not in ('up', 'down'):
        abort(400, "Invalid vote direction")

    user = get_user()
    cast_box_vote(box_id, user["id"], 1 if direction == 'up' else -1)
    return jsonify({"ok": True, "score": get_box_score(box_id), "userVote": get_user_box_vote(box_id, user["id"])})

@bp.route('/<slug>/boxes/<int:box_id>/comments', methods=['POST'])
@login_required()
def add_box_comment(slug, box_id):
    roadmap, box = _get_roadmap_box_or_404(slug, box_id)

    body = request.form.get('body', '').strip()
    if not body:
        abort(400, "Comment cannot be empty")

    parent_comment_id = request.form.get('parentCommentId', type=int)
    if parent_comment_id is not None:
        parent = get_box_comment(parent_comment_id)
        if not parent or parent["boxId"] != box_id or parent["parentCommentId"] is not None:
            abort(400, "Invalid parent comment")

    comment_id = create_box_comment(box_id, get_user(), body, parent_comment_id)
    comment = get_box_comment(comment_id)
    send_discord_notification("RoadmapComment", f"\U0001F4AC **{comment['authorUsername']}** commented on step *{box['title']}* ({roadmap['name']})")
    return jsonify({
        "ok": True,
        "comment": {
            "id": comment["id"],
            "authorId": comment["authorId"],
            "authorUsername": comment["authorUsername"],
            "body": comment["body"],
            "parentCommentId": comment["parentCommentId"],
            "score": 0,
            "userUpvoted": False,
            "createdAtIso": comment["createdAt"].replace(tzinfo=timezone.utc).isoformat(),
        }
    })

@bp.route('/<slug>/boxes/<int:box_id>/comments/<int:comment_id>/delete', methods=['POST'])
@login_required()
def remove_box_comment(slug, box_id, comment_id):
    _get_roadmap_box_or_404(slug, box_id)
    comment = get_box_comment(comment_id)
    if not comment or comment["boxId"] != box_id:
        abort(404)

    user = get_user()
    if comment["authorId"] != user["id"] and user["auth"] < get_auth("MODERATOR"):
        abort(403, "Cannot delete another user's comment")

    delete_box_comment(comment_id)
    return jsonify({"ok": True})

@bp.route('/<slug>/boxes/<int:box_id>/comments/<int:comment_id>/upvote', methods=['POST'])
@login_required()
def upvote_box_comment(slug, box_id, comment_id):
    _get_roadmap_box_or_404(slug, box_id)
    comment = get_box_comment(comment_id)
    if not comment or comment["boxId"] != box_id:
        abort(404)

    user = get_user()
    upvoted = toggle_comment_upvote(comment_id, user["id"])
    return jsonify({"ok": True, "upvoted": upvoted, "score": get_comment_score(comment_id)})
