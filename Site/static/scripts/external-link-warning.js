(function () {
    const overlay = document.getElementById('leaving-modal-overlay');
    const destinationEl = document.getElementById('leaving-modal-destination');
    const continueLink = document.getElementById('leaving-modal-continue');
    const cancelBtn = document.getElementById('leaving-modal-cancel');

    let pendingHref = null;
    let pendingTarget = null;

    function isExternalLink(anchor) {
        if (!anchor.href) return false;

        let url;
        try {
            url = new URL(anchor.href, window.location.href);
        } catch (err) {
            return false;
        }

        if (url.protocol !== 'http:' && url.protocol !== 'https:') return false;
        return url.hostname !== window.location.hostname;
    }

    function openModal(anchor) {
        pendingHref = anchor.href;
        pendingTarget = anchor.target || '_self';
        destinationEl.textContent = new URL(anchor.href).hostname;
        overlay.classList.add('open');
    }

    function closeModal() {
        overlay.classList.remove('open');
        pendingHref = null;
        pendingTarget = null;
    }

    document.addEventListener('click', function (e) {
        const anchor = e.target.closest('a');
        if (!anchor || !isExternalLink(anchor)) return;

        e.preventDefault();
        openModal(anchor);
    });

    continueLink.addEventListener('click', function (e) {
        e.preventDefault();
        if (!pendingHref) return;

        if (pendingTarget === '_blank') {
            window.open(pendingHref, '_blank', 'noopener,noreferrer');
        } else {
            window.location.href = pendingHref;
        }
        closeModal();
    });

    cancelBtn.addEventListener('click', closeModal);

    overlay.addEventListener('click', function (e) {
        if (e.target === overlay) closeModal();
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && overlay.classList.contains('open')) closeModal();
    });
})();
