document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".audit-time[data-timestamp]").forEach((el) => {
        const date = new Date(el.dataset.timestamp);
        if (!isNaN(date)) {
            el.textContent = date.toLocaleString();
        }
    });
});
