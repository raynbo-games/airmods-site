(function () {
    const canvas = document.getElementById('roadmap-canvas');
    const svg = document.getElementById('roadmap-arrows-svg');
    const BOX_WIDTH = 200;
    const BOX_HEIGHT = 60;

    const boxes = {};
    BOXES.forEach(function (b) { boxes[b.id] = b; });
    const arrows = ARROWS.slice();

    function boxEdgePoints(a, b) {
        const ay = a.y + BOX_HEIGHT / 2;
        const by = b.y + BOX_HEIGHT / 2;
        let x1, x2;
        if (b.x >= a.x) {
            x1 = a.x + BOX_WIDTH; x2 = b.x;
        } else {
            x1 = a.x; x2 = b.x + BOX_WIDTH;
        }
        return { x1: x1, y1: ay, x2: x2, y2: by };
    }

    function arrowPath(a, b) {
        const p = boxEdgePoints(a, b);
        const dx = Math.max(60, Math.abs(p.x2 - p.x1) / 2);
        return `M ${p.x1},${p.y1} C ${p.x1 + dx},${p.y1} ${p.x2 - dx},${p.y2} ${p.x2},${p.y2}`;
    }

    function makeArrowPath(arrow) {
        const a = boxes[arrow.fromBoxId];
        const b = boxes[arrow.toBoxId];
        if (!a || !b) return null;

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', arrowPath(a, b));
        path.setAttribute('class', 'roadmap-arrow-path');
        path.setAttribute('marker-end', 'url(#arrowhead)');
        path.dataset.arrowId = arrow.id;

        if (CAN_EDIT) {
            path.addEventListener('click', function (e) {
                e.stopPropagation();
                if (!confirm('Delete this connection?')) return;
                fetch(`/roadmaps/${ROADMAP_SLUG}/arrows/${arrow.id}/delete`, { method: 'POST' })
                    .then(function () { path.remove(); });
            });
        }

        return path;
    }

    function renderAllArrows() {
        svg.querySelectorAll('.roadmap-arrow-path').forEach(function (el) { el.remove(); });
        arrows.forEach(function (arrow) {
            const path = makeArrowPath(arrow);
            if (path) svg.appendChild(path);
        });
    }

    function updateArrowsForBox(boxId) {
        svg.querySelectorAll('.roadmap-arrow-path').forEach(function (el) {
            const arrow = arrows.find(function (a) { return String(a.id) === el.dataset.arrowId; });
            if (!arrow) return;
            if (arrow.fromBoxId === boxId || arrow.toBoxId === boxId) {
                const a = boxes[arrow.fromBoxId];
                const b = boxes[arrow.toBoxId];
                if (a && b) el.setAttribute('d', arrowPath(a, b));
            }
        });
    }

    function resizeSvg() {
        svg.setAttribute('width', canvas.scrollWidth);
        svg.setAttribute('height', canvas.scrollHeight);
    }

    renderAllArrows();
    resizeSvg();

    let connectMode = false;
    let connectFrom = null;

    window.toggleConnectMode = function () {
        connectMode = !connectMode;
        connectFrom = null;
        document.querySelectorAll('.roadmap-box').forEach(function (el) { el.classList.remove('connect-selected'); });
        const btn = document.getElementById('connect-mode-btn');
        if (btn) btn.classList.toggle('active', connectMode);
    };

    let dragState = null;

    document.querySelectorAll('.roadmap-box').forEach(function (el) {
        const boxId = parseInt(el.dataset.boxId, 10);

        el.addEventListener('mousedown', function (e) {
            if (!CAN_EDIT || connectMode) return;
            dragState = {
                boxId: boxId,
                el: el,
                startX: e.clientX,
                startY: e.clientY,
                origX: boxes[boxId].x,
                origY: boxes[boxId].y,
                moved: false,
            };
            e.preventDefault();
        });

        el.addEventListener('click', function () {
            if (dragState && dragState.moved) { dragState = null; return; }

            if (connectMode) {
                if (connectFrom === null) {
                    connectFrom = boxId;
                    el.classList.add('connect-selected');
                } else if (connectFrom !== boxId) {
                    const fromId = connectFrom;
                    fetch(`/roadmaps/${ROADMAP_SLUG}/arrows`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `fromBoxId=${fromId}&toBoxId=${boxId}`,
                    })
                        .then(function (r) { return r.json(); })
                        .then(function (data) {
                            if (data.ok) {
                                arrows.push({ id: data.id, fromBoxId: fromId, toBoxId: boxId });
                                renderAllArrows();
                            }
                        });
                    document.querySelectorAll('.roadmap-box').forEach(function (b) { b.classList.remove('connect-selected'); });
                    connectFrom = null;
                } else {
                    el.classList.remove('connect-selected');
                    connectFrom = null;
                }
                return;
            }

            openDetailModal(boxes[boxId]);
        });
    });

    document.addEventListener('mousemove', function (e) {
        if (!dragState) return;
        const dx = e.clientX - dragState.startX;
        const dy = e.clientY - dragState.startY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragState.moved = true;
        if (!dragState.moved) return;

        const newX = Math.max(0, dragState.origX + dx);
        const newY = Math.max(0, dragState.origY + dy);
        dragState.el.style.left = newX + 'px';
        dragState.el.style.top = newY + 'px';
        boxes[dragState.boxId].x = newX;
        boxes[dragState.boxId].y = newY;
        updateArrowsForBox(dragState.boxId);
        resizeSvg();
    });

    // Defers clearing dragState by a tick since the click event fires right after mouseup,
    // and the box's click handler still needs to see dragState.moved on that same click.
    document.addEventListener('mouseup', function () {
        if (!dragState) return;
        if (dragState.moved) {
            const boxId = dragState.boxId;
            fetch(`/roadmaps/${ROADMAP_SLUG}/boxes/${boxId}/position`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `x=${boxes[boxId].x}&y=${boxes[boxId].y}`,
            });
        }
        setTimeout(function () { dragState = null; }, 0);
    });

    const detailOverlay = document.getElementById('roadmap-detail-overlay');
    const detailTitle = document.getElementById('roadmap-detail-title');
    const detailStatus = document.getElementById('roadmap-detail-status');
    const detailDescription = document.getElementById('roadmap-detail-description');
    const detailEditBtn = document.getElementById('roadmap-detail-edit-btn');
    const detailCloseBtn = document.getElementById('roadmap-detail-close-btn');
    const voteUpBtn = document.getElementById('roadmap-detail-vote-up');
    const voteDownBtn = document.getElementById('roadmap-detail-vote-down');
    const voteScoreEl = document.getElementById('roadmap-detail-vote-score');
    const commentListEl = document.getElementById('roadmap-detail-comment-list');
    const commentFormEl = document.getElementById('roadmap-detail-comment-form');
    const commentInputEl = document.getElementById('roadmap-detail-comment-input');
    const commentSubmitBtn = document.getElementById('roadmap-detail-comment-submit');
    const loginPromptEl = document.getElementById('roadmap-detail-login-prompt');
    let detailBoxId = null;
    let detailUserVote = 0;
    let detailCanModerate = false;

    function statusLabel(status) {
        return status.replace('_', ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    }

    function bumpBoxCommentCount(delta) {
        const commentsEl = document.querySelector(`#box-${detailBoxId} .roadmap-box-comments`);
        if (!commentsEl) return;
        const count = Math.max(0, (parseInt(commentsEl.textContent.replace(/\D/g, ''), 10) || 0) + delta);
        commentsEl.textContent = `\u{1F4AC} ${count}`;
    }

    // Moderators still see a deleted comment (for audit purposes), so refetch to re-render it
    // in the deleted state instead of removing it outright as a non-moderator deletion would.
    function deleteComment(card, commentId) {
        if (!confirm('Delete this comment?')) return;
        fetch(`/roadmaps/${ROADMAP_SLUG}/boxes/${detailBoxId}/comments/${commentId}/delete`, { method: 'POST' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.ok) return;
                bumpBoxCommentCount(-1);
                if (detailCanModerate) {
                    loadDiscussion(detailBoxId);
                } else {
                    card.remove();
                }
            });
    }

    function toggleReplyForm(card, parentId) {
        const existing = card.querySelector('.comment-reply-form');
        if (existing) { existing.remove(); return; }

        const form = document.createElement('div');
        form.className = 'comment-reply-form';

        const textarea = document.createElement('textarea');
        textarea.className = 'form-control form-dark-input admin-form-textarea';
        textarea.rows = 2;
        textarea.placeholder = 'Write a reply...';
        form.appendChild(textarea);

        const submitBtn = document.createElement('button');
        submitBtn.type = 'button';
        submitBtn.className = 'btn btn-primary admin-form-submit';
        submitBtn.textContent = 'Post Reply';
        submitBtn.addEventListener('click', function () {
            const body = textarea.value.trim();
            if (!body) return;
            fetch(`/roadmaps/${ROADMAP_SLUG}/boxes/${detailBoxId}/comments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `body=${encodeURIComponent(body)}&parentCommentId=${parentId}`,
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data.ok) return;
                    bumpBoxCommentCount(1);
                    loadDiscussion(detailBoxId);
                });
        });
        form.appendChild(submitBtn);

        card.appendChild(form);
        textarea.focus();
    }

    // A deleted comment is only ever rendered for moderators, shown audit-only with no actions.
    function renderComment(comment, isReply) {
        if (comment.deleted && !detailCanModerate) return null;

        const card = document.createElement('div');
        card.className = 'comment-card' + (isReply ? ' comment-reply' : '') + (comment.deleted ? ' comment-deleted' : '');
        card.dataset.commentId = comment.id;
        if (isReply) card.dataset.parentId = comment.parentCommentId;

        const meta = document.createElement('div');
        meta.className = 'comment-meta';
        meta.textContent = comment.authorUsername;
        if (comment.deleted) {
            const badge = document.createElement('span');
            badge.className = 'suggestion-status-badge status-hidden';
            badge.textContent = 'deleted';
            meta.appendChild(document.createTextNode(' '));
            meta.appendChild(badge);
        }
        card.appendChild(meta);

        const body = document.createElement('div');
        body.className = 'comment-body';
        body.textContent = comment.body;
        card.appendChild(body);

        if (comment.deleted) {
            return card;
        }

        const row = document.createElement('div');
        row.className = 'mod-action-row';

        const upvoteBtn = document.createElement('button');
        upvoteBtn.type = 'button';
        upvoteBtn.className = 'mod-action-btn comment-upvote-btn' + (comment.userUpvoted ? ' active' : '');
        upvoteBtn.textContent = `▲ ${comment.score}`;
        if (IS_LOGGED_IN) {
            upvoteBtn.addEventListener('click', function () {
                fetch(`/roadmaps/${ROADMAP_SLUG}/boxes/${detailBoxId}/comments/${comment.id}/upvote`, { method: 'POST' })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (!data.ok) return;
                        upvoteBtn.textContent = `▲ ${data.score}`;
                        upvoteBtn.classList.toggle('active', data.upvoted);
                    });
            });
        }
        row.appendChild(upvoteBtn);

        if (!isReply && IS_LOGGED_IN) {
            const replyBtn = document.createElement('button');
            replyBtn.type = 'button';
            replyBtn.className = 'mod-action-btn';
            replyBtn.textContent = 'Reply';
            replyBtn.addEventListener('click', function () { toggleReplyForm(card, comment.id); });
            row.appendChild(replyBtn);
        }

        if (IS_LOGGED_IN && (comment.authorId === CURRENT_USER_ID || detailCanModerate)) {
            const delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 'mod-action-btn danger';
            delBtn.textContent = 'Delete';
            delBtn.addEventListener('click', function () { deleteComment(card, comment.id); });
            row.appendChild(delBtn);
        }

        card.appendChild(row);
        return card;
    }

    function updateVoteUI() {
        voteUpBtn.classList.toggle('active-up', detailUserVote === 1);
        voteDownBtn.classList.toggle('active-down', detailUserVote === -1);
    }

    function loadDiscussion(boxId) {
        commentListEl.innerHTML = '<p class="info-description">Loading...</p>';
        fetch(`/roadmaps/${ROADMAP_SLUG}/boxes/${boxId}/discussion`)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                voteScoreEl.textContent = data.score;
                detailUserVote = data.userVote;
                detailCanModerate = data.canModerate;
                updateVoteUI();

                commentListEl.innerHTML = '';
                if (data.comments.length === 0) {
                    commentListEl.innerHTML = '<p class="info-description">No comments yet.</p>';
                    return;
                }

                const repliesByParent = {};
                data.comments.forEach(function (c) {
                    if (!c.parentCommentId) return;
                    if (!repliesByParent[c.parentCommentId]) repliesByParent[c.parentCommentId] = [];
                    repliesByParent[c.parentCommentId].push(c);
                });

                data.comments.filter(function (c) { return !c.parentCommentId; }).forEach(function (c) {
                    const el = renderComment(c, false);
                    if (el) commentListEl.appendChild(el);
                    (repliesByParent[c.id] || []).forEach(function (reply) {
                        const replyEl = renderComment(reply, true);
                        if (replyEl) commentListEl.appendChild(replyEl);
                    });
                });
            });
    }

    window.openDetailModal = function (box) {
        detailBoxId = box.id;
        detailTitle.textContent = box.title;
        detailStatus.textContent = statusLabel(box.status);
        detailStatus.className = 'roadmap-status-badge status-' + box.status;
        detailDescription.textContent = box.description || 'No description provided.';
        voteScoreEl.textContent = box.score || 0;
        detailUserVote = 0;
        updateVoteUI();

        if (IS_LOGGED_IN) {
            commentFormEl.classList.remove('hidden-form');
            loginPromptEl.classList.add('hidden-form');
        } else {
            commentFormEl.classList.add('hidden-form');
            loginPromptEl.classList.remove('hidden-form');
        }
        commentInputEl.value = '';

        detailOverlay.classList.add('open');
        loadDiscussion(box.id);
    };

    if (detailCloseBtn) detailCloseBtn.addEventListener('click', function () { detailOverlay.classList.remove('open'); });
    detailOverlay.addEventListener('click', function (e) { if (e.target === detailOverlay) detailOverlay.classList.remove('open'); });

    function castDetailVote(direction) {
        if (!IS_LOGGED_IN || detailBoxId === null) return;
        fetch(`/roadmaps/${ROADMAP_SLUG}/boxes/${detailBoxId}/vote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `direction=${direction}`,
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.ok) return;
                voteScoreEl.textContent = data.score;
                detailUserVote = data.userVote;
                updateVoteUI();
                if (boxes[detailBoxId]) boxes[detailBoxId].score = data.score;
                const scoreValueEl = document.querySelector(`#box-${detailBoxId} .roadmap-box-score-value`);
                if (scoreValueEl) scoreValueEl.textContent = data.score;
            });
    }

    if (voteUpBtn) voteUpBtn.addEventListener('click', function () { castDetailVote('up'); });
    if (voteDownBtn) voteDownBtn.addEventListener('click', function () { castDetailVote('down'); });

    if (commentSubmitBtn) {
        commentSubmitBtn.addEventListener('click', function () {
            const body = commentInputEl.value.trim();
            if (!body || detailBoxId === null) return;
            fetch(`/roadmaps/${ROADMAP_SLUG}/boxes/${detailBoxId}/comments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `body=${encodeURIComponent(body)}`,
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data.ok) return;
                    const emptyMsg = commentListEl.querySelector('.info-description');
                    if (emptyMsg) emptyMsg.remove();
                    commentListEl.appendChild(renderComment(data.comment, false));
                    commentInputEl.value = '';
                    bumpBoxCommentCount(1);
                });
        });
    }

    if (CAN_EDIT && detailEditBtn) {
        detailEditBtn.addEventListener('click', function () {
            detailOverlay.classList.remove('open');
            openBoxModal(boxes[detailBoxId]);
        });
    }

    if (CAN_EDIT) {
        const boxOverlay = document.getElementById('roadmap-box-overlay');
        const boxForm = document.getElementById('roadmap-box-form');
        const boxModalTitle = document.getElementById('roadmap-box-modal-title');
        const titleInput = document.getElementById('roadmap-box-title-input');
        const descInput = document.getElementById('roadmap-box-description-input');
        const statusInput = document.getElementById('roadmap-box-status-input');
        const xInput = document.getElementById('roadmap-box-x-input');
        const yInput = document.getElementById('roadmap-box-y-input');
        const cancelBtn = document.getElementById('roadmap-box-cancel-btn');
        const deleteForm = document.getElementById('roadmap-box-delete-form');

        window.openBoxModal = function (box) {
            if (box) {
                boxModalTitle.textContent = 'Edit Step';
                titleInput.value = box.title;
                descInput.value = box.description || '';
                statusInput.value = box.status;
                xInput.value = box.x;
                yInput.value = box.y;
                boxForm.action = `/roadmaps/${ROADMAP_SLUG}/boxes/${box.id}`;
                deleteForm.action = `/roadmaps/${ROADMAP_SLUG}/boxes/${box.id}/delete`;
                deleteForm.classList.remove('hidden-form');
            } else {
                boxModalTitle.textContent = 'Add Step';
                titleInput.value = '';
                descInput.value = '';
                statusInput.value = 'planned';
                xInput.value = 40;
                yInput.value = 40;
                boxForm.action = ADD_BOX_URL;
                deleteForm.classList.add('hidden-form');
            }
            boxOverlay.classList.add('open');
        };

        cancelBtn.addEventListener('click', function () { boxOverlay.classList.remove('open'); });
        boxOverlay.addEventListener('click', function (e) { if (e.target === boxOverlay) boxOverlay.classList.remove('open'); });

        deleteForm.addEventListener('submit', function (e) {
            if (!confirm('Delete this step? Any connected arrows will also be removed.')) e.preventDefault();
        });

        const renameOverlay = document.getElementById('roadmap-rename-overlay');
        const renameCancelBtn = document.getElementById('roadmap-rename-cancel-btn');
        window.openRenameModal = function () { renameOverlay.classList.add('open'); };
        if (renameCancelBtn) renameCancelBtn.addEventListener('click', function () { renameOverlay.classList.remove('open'); });
        renameOverlay.addEventListener('click', function (e) { if (e.target === renameOverlay) renameOverlay.classList.remove('open'); });
    }
})();
