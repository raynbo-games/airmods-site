function formatDate(value) {
    const date = new Date(value);
    if (isNaN(date)) return "Unknown";
    return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

document.addEventListener("DOMContentLoaded", () => {
    const isBanned = !!org_data["adminBanned"];

    document.getElementById("org-info").innerHTML = `
    <div class="info-header">
        <img id="org-icon" class="info-icon" alt="Organization Icon" src="${image_url}">
        <div class="info-header-text">
            <h1>${org_data["name"]}</h1>
            <p class="info-description">${org_data["description"]}</p>
            <div class="info-chips">
                <span class="info-chip info-chip-badge ${isBanned ? "info-chip-warning" : ""}">${isBanned ? "Admin Banned" : "Active"}</span>
            </div>
        </div>
    </div>

    <div class="info-stats-grid">
        <div class="info-stat"><span class="info-stat-label">Created</span><span class="info-stat-value">${formatDate(org_data["createdAt"])}</span></div>
    </div>
    `;
});
