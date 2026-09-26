document.querySelectorAll('.infra-logs-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
        const appId = btn.dataset.appId;
        const output = document.getElementById(`logs-${appId}`);
        output.hidden = false;
        output.textContent = 'Loading...';
        btn.disabled = true;

        fetch(`/admin/infrastructure/apps/${appId}/logs`)
            .then((res) => res.json())
            .then((data) => { output.textContent = data.logs; })
            .catch(() => { output.textContent = 'Failed to load logs.'; })
            .finally(() => { btn.disabled = false; });
    });
});
