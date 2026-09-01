(function () {
    const overlay = document.getElementById('reason-modal-overlay');
    if (!overlay) return;

    const reasonInput = document.getElementById('reason-modal-input');
    const confirmBtn = document.getElementById('reason-modal-confirm');
    const cancelBtn = document.getElementById('reason-modal-cancel');
    const actionLabel = document.getElementById('reason-modal-action-label');

    let pendingForm = null;

    document.querySelectorAll('form[data-requires-reason]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (form.dataset.reasonConfirmed === 'true') return;

            e.preventDefault();
            pendingForm = form;
            actionLabel.textContent = form.dataset.requiresReason || 'this action';
            reasonInput.value = '';
            overlay.classList.add('open');
            reasonInput.focus();
        });
    });

    function closeModal() {
        overlay.classList.remove('open');
        pendingForm = null;
    }

    confirmBtn.addEventListener('click', function () {
        const reason = reasonInput.value.trim();
        if (!reason) {
            reasonInput.focus();
            return;
        }
        if (!pendingForm) return;

        let reasonField = pendingForm.querySelector('input[name="reason"]');
        if (!reasonField) {
            reasonField = document.createElement('input');
            reasonField.type = 'hidden';
            reasonField.name = 'reason';
            pendingForm.appendChild(reasonField);
        }
        reasonField.value = reason;
        pendingForm.dataset.reasonConfirmed = 'true';

        const formToSubmit = pendingForm;
        closeModal();
        formToSubmit.submit();
    });

    reasonInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            confirmBtn.click();
        }
    });

    cancelBtn.addEventListener('click', closeModal);

    overlay.addEventListener('click', function (e) {
        if (e.target === overlay) closeModal();
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && overlay.classList.contains('open')) closeModal();
    });
})();
