from datetime import timezone
from flask import Blueprint, render_template, redirect, url_for, request, abort
from Site.code.auth.database import get_auth
from Site.code.auth.main import login_required, auth_required, get_user
from Site.code.admin.database import add_audit_log
from Site.code.community.webhook import send_discord_notification, build_embed
from Site.code.community.database import (
    create_suggestion, get_suggestion, get_suggestions, get_pending_suggestions,
    update_suggestion, set_suggestion_status, delete_suggestion,
    get_suggestion_score, get_user_vote, cast_vote,
    create_comment, get_comments, get_comment, get_pending_comments,
    update_comment, set_comment_status,
    get_notifications, mark_notifications_read, add_notification
)

bp = Blueprint('community', __name__, url_prefix='/community')

@bp.context_processor
def inject_community_global():
    return dict(title="Community")

def require_reason():
    reason = request.form.get('reason', '').strip()
    if not reason:
        abort(400, "A reason is required for this action")
    return reason

@bp.route('')
def root():
    suggestions = get_suggestions()
    for suggestion in suggestions:
        suggestion["score"] = get_suggestion_score(suggestion["id"])
    return render_template('community/index.html', suggestions=suggestions)

@bp.route('/suggestions/new', methods=['GET', 'POST'])
@login_required()
def new_suggestion():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        if not title or not body:
            abort(400, "Title and body are required")

        suggestion_id, status = create_suggestion(get_user(), title, body)
        return redirect(url_for('community.view_suggestion', suggestion_id=suggestion_id))

    return render_template('community/new_suggestion.html')

@bp.route('/suggestions/<int:suggestion_id>')
def view_suggestion(suggestion_id):
    """Fetch every comment regardless of status so reply->parent linkage never breaks on a
    parent invisible to this viewer; per-comment visibility is decided at render time instead."""
    suggestion = get_suggestion(suggestion_id)
    if not suggestion:
        abort(404)

    user = get_user()
    is_moderator = bool(user and user["auth"] >= get_auth("MODERATOR"))

    if suggestion["status"] != "visible":
        is_owner = bool(user and suggestion["authorId"] == user["id"])
        if not is_owner and not is_moderator:
            abort(404)

    comments_by_id = {}
    top_level_comments = []
    for comment in get_comments(suggestion_id, include_hidden=True):
        comment = dict(comment)
        comment["replies"] = []
        comment["visible_to_viewer"] = comment["status"] == "visible" or is_moderator
        comments_by_id[comment["id"]] = comment
        if comment["parentCommentId"]:
            parent = comments_by_id.get(comment["parentCommentId"])
            if parent:
                parent["replies"].append(comment)
        else:
            top_level_comments.append(comment)

    score = get_suggestion_score(suggestion_id)
    user_vote = get_user_vote(suggestion_id, user["id"]) if user else 0

    return render_template(
        'community/suggestion.html',
        suggestion=suggestion,
        comments=top_level_comments,
        score=score,
        user_vote=user_vote,
        is_moderator=is_moderator,
    )

@bp.route('/suggestions/<int:suggestion_id>/vote', methods=['POST'])
@login_required()
def vote_suggestion(suggestion_id):
    suggestion = get_suggestion(suggestion_id)
    if not suggestion or suggestion["status"] != "visible":
        abort(404)

    direction = request.form.get('direction')
    if direction not in ('up', 'down'):
        abort(400, "Invalid vote direction")

    cast_vote(suggestion_id, get_user()["id"], 1 if direction == 'up' else -1)
    return redirect(url_for('community.view_suggestion', suggestion_id=suggestion_id))

@bp.route('/suggestions/<int:suggestion_id>/comments', methods=['POST'])
@login_required()
def post_comment(suggestion_id):
    suggestion = get_suggestion(suggestion_id)
    if not suggestion or suggestion["status"] != "visible":
        abort(404)

    body = request.form.get('body', '').strip()
    if not body:
        abort(400, "Comment cannot be empty")

    parent_comment = None
    parent_comment_id = request.form.get('parentCommentId', type=int)
    if parent_comment_id is not None:
        parent_comment = get_comment(parent_comment_id)
        if not parent_comment or parent_comment["suggestionId"] != suggestion_id or parent_comment["parentCommentId"] is not None:
            abort(400, "Invalid parent comment")

    create_comment(get_user(), suggestion, body, parent_comment)
    return redirect(url_for('community.view_suggestion', suggestion_id=suggestion_id))

@bp.route('/suggestions/<int:suggestion_id>/hide', methods=['POST'])
@auth_required("MODERATOR")
def hide_suggestion(suggestion_id):
    suggestion = get_suggestion(suggestion_id)
    if not suggestion:
        abort(404)
    reason = require_reason()

    new_status = "hidden" if suggestion["status"] == "visible" else "visible"
    set_suggestion_status(suggestion_id, new_status)

    actor = get_user()
    target = {"id": suggestion["authorId"], "username": suggestion["authorUsername"]}
    action = "hide_suggestion" if new_status == "hidden" else "unhide_suggestion"
    add_audit_log(actor, target, action, reason, details=f'Suggestion "{suggestion["title"]}" {"hidden" if new_status == "hidden" else "unhidden"}')

    if new_status == "hidden" and suggestion["authorId"] != actor["id"]:
        add_notification(
            suggestion["authorId"],
            f'Your suggestion "{suggestion["title"]}" was hidden by a moderator: {reason}',
            url=url_for('community.view_suggestion', suggestion_id=suggestion_id)
        )

    return redirect(url_for('community.view_suggestion', suggestion_id=suggestion_id))

@bp.route('/suggestions/<int:suggestion_id>/edit', methods=['POST'])
@auth_required("MODERATOR")
def edit_suggestion(suggestion_id):
    suggestion = get_suggestion(suggestion_id)
    if not suggestion:
        abort(404)
    reason = require_reason()

    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()
    if not title or not body:
        abort(400, "Title and body are required")

    old_title = suggestion["title"]
    update_suggestion(suggestion_id, title, body)

    actor = get_user()
    target = {"id": suggestion["authorId"], "username": suggestion["authorUsername"]}
    add_audit_log(actor, target, "edit_suggestion", reason, details=f'Suggestion "{old_title}" edited by a moderator')
    embed = build_embed("✏️ Suggestion Edited", fields=[("Moderator", actor["username"]), ("Title", title, False)])
    send_discord_notification("edited_post", embed=embed)

    if suggestion["authorId"] != actor["id"]:
        add_notification(
            suggestion["authorId"],
            f'Your suggestion "{old_title}" was edited by a moderator: {reason}',
            url=url_for('community.view_suggestion', suggestion_id=suggestion_id)
        )

    return redirect(url_for('community.view_suggestion', suggestion_id=suggestion_id))

@bp.route('/suggestions/<int:suggestion_id>/delete', methods=['POST'])
@auth_required("MODERATOR")
def remove_suggestion(suggestion_id):
    suggestion = get_suggestion(suggestion_id)
    if not suggestion:
        abort(404)
    reason = require_reason()

    delete_suggestion(suggestion_id)

    actor = get_user()
    target = {"id": suggestion["authorId"], "username": suggestion["authorUsername"]}
    add_audit_log(actor, target, "delete_suggestion", reason, details=f'Suggestion "{suggestion["title"]}" deleted')

    if suggestion["authorId"] != actor["id"]:
        add_notification(suggestion["authorId"], f'Your suggestion "{suggestion["title"]}" was deleted by a moderator: {reason}')

    return redirect(url_for('community.root'))

@bp.route('/comments/<int:comment_id>/hide', methods=['POST'])
@auth_required("MODERATOR")
def hide_comment(comment_id):
    comment = get_comment(comment_id)
    if not comment:
        abort(404)
    reason = require_reason()

    new_status = "hidden" if comment["status"] == "visible" else "visible"
    set_comment_status(comment_id, new_status)

    actor = get_user()
    target = {"id": comment["authorId"], "username": comment["authorUsername"]}
    action = "hide_comment" if new_status == "hidden" else "unhide_comment"
    add_audit_log(actor, target, action, reason, details=f'Comment {"hidden" if new_status == "hidden" else "unhidden"}')

    if new_status == "hidden" and comment["authorId"] != actor["id"]:
        add_notification(
            comment["authorId"],
            f'Your comment was hidden by a moderator: {reason}',
            url=url_for('community.view_suggestion', suggestion_id=comment["suggestionId"])
        )

    return redirect(url_for('community.view_suggestion', suggestion_id=comment["suggestionId"]))

@bp.route('/comments/<int:comment_id>/edit', methods=['POST'])
@auth_required("MODERATOR")
def edit_comment(comment_id):
    comment = get_comment(comment_id)
    if not comment:
        abort(404)
    reason = require_reason()

    body = request.form.get('body', '').strip()
    if not body:
        abort(400, "Comment cannot be empty")

    update_comment(comment_id, body)

    actor = get_user()
    target = {"id": comment["authorId"], "username": comment["authorUsername"]}
    add_audit_log(actor, target, "edit_comment", reason, details="Comment edited by a moderator")

    if comment["authorId"] != actor["id"]:
        add_notification(
            comment["authorId"],
            f'Your comment was edited by a moderator: {reason}',
            url=url_for('community.view_suggestion', suggestion_id=comment["suggestionId"])
        )

    return redirect(url_for('community.view_suggestion', suggestion_id=comment["suggestionId"]))

@bp.route('/comments/<int:comment_id>/delete', methods=['POST'])
@auth_required("MODERATOR")
def remove_comment(comment_id):
    comment = get_comment(comment_id)
    if not comment:
        abort(404)
    reason = require_reason()

    suggestion_id = comment["suggestionId"]
    set_comment_status(comment_id, "deleted")

    actor = get_user()
    target = {"id": comment["authorId"], "username": comment["authorUsername"]}
    add_audit_log(actor, target, "delete_comment", reason, details="Comment deleted by a moderator")

    if comment["authorId"] != actor["id"]:
        add_notification(
            comment["authorId"],
            f'Your comment was deleted by a moderator: {reason}',
            url=url_for('community.view_suggestion', suggestion_id=suggestion_id)
        )

    return redirect(url_for('community.view_suggestion', suggestion_id=suggestion_id))

@bp.route('/review')
@auth_required("MODERATOR")
def review():
    return render_template('community/review.html', suggestions=get_pending_suggestions(), comments=get_pending_comments())

@bp.route('/review/suggestions/<int:suggestion_id>/approve', methods=['POST'])
@auth_required("MODERATOR")
def approve_suggestion(suggestion_id):
    suggestion = get_suggestion(suggestion_id)
    if not suggestion:
        abort(404)

    set_suggestion_status(suggestion_id, "visible")
    actor = get_user()
    target = {"id": suggestion["authorId"], "username": suggestion["authorUsername"]}
    add_audit_log(actor, target, "approve_suggestion", "Passed manual review", details=f'Suggestion "{suggestion["title"]}" approved')
    embed = build_embed("\U0001F4A1 New Suggestion Posted", fields=[("Author", suggestion["authorUsername"]), ("Title", suggestion["title"], False)])
    send_discord_notification("new_post", embed=embed)

    return redirect(url_for('community.review'))

@bp.route('/review/suggestions/<int:suggestion_id>/reject', methods=['POST'])
@auth_required("MODERATOR")
def reject_suggestion(suggestion_id):
    suggestion = get_suggestion(suggestion_id)
    if not suggestion:
        abort(404)
    reason = require_reason()

    set_suggestion_status(suggestion_id, "rejected")
    actor = get_user()
    target = {"id": suggestion["authorId"], "username": suggestion["authorUsername"]}
    add_audit_log(actor, target, "reject_suggestion", reason, details=f'Suggestion "{suggestion["title"]}" rejected')
    add_notification(suggestion["authorId"], f'Your suggestion "{suggestion["title"]}" was rejected during review: {reason}')

    return redirect(url_for('community.review'))

@bp.route('/review/comments/<int:comment_id>/approve', methods=['POST'])
@auth_required("MODERATOR")
def approve_comment(comment_id):
    comment = get_comment(comment_id)
    if not comment:
        abort(404)

    set_comment_status(comment_id, "visible")
    actor = get_user()
    target = {"id": comment["authorId"], "username": comment["authorUsername"]}
    add_audit_log(actor, target, "approve_comment", "Passed manual review", details="Comment approved")
    embed = build_embed("\U0001F4AC New Comment (Approved After Review)", fields=[("Author", comment["authorUsername"])])
    send_discord_notification("comment", embed=embed)

    return redirect(url_for('community.review'))

@bp.route('/review/comments/<int:comment_id>/reject', methods=['POST'])
@auth_required("MODERATOR")
def reject_comment(comment_id):
    comment = get_comment(comment_id)
    if not comment:
        abort(404)
    reason = require_reason()

    set_comment_status(comment_id, "rejected")
    actor = get_user()
    target = {"id": comment["authorId"], "username": comment["authorUsername"]}
    add_audit_log(actor, target, "reject_comment", reason, details="Comment rejected")
    add_notification(comment["authorId"], f'Your comment was rejected during review: {reason}')

    return redirect(url_for('community.review'))

@bp.route('/inbox')
@login_required()
def inbox():
    user = get_user()
    notifications = []
    for notification in get_notifications(user["id"]):
        notification = dict(notification)
        notification["createdAtIso"] = notification["createdAt"].replace(tzinfo=timezone.utc).isoformat()
        notifications.append(notification)

    mark_notifications_read(user["id"])
    return render_template('community/inbox.html', notifications=notifications)
