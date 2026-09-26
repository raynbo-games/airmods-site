function formatDate(value) {
    const date = new Date(value);
    if (isNaN(date)) return "Unknown";
    return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

document.addEventListener("DOMContentLoaded", () => {
    let links = "";
    for (const link of game_data["links"]) {
        const label = link.type ? link.type.charAt(0) + link.type.slice(1).toLowerCase() : "Link";
        links += `<a href="${link.url}" class="info-chip" target="_blank" rel="noopener noreferrer">${label}</a>`;
    }

    const platforms = game_data["platforms"].join(", ") || "None";
    const isArchived = !!game_data["archivedAt"];

    document.getElementById("game-info").innerHTML = `
    <div class="info-header">
        <img id="game-icon" class="info-icon" alt="Game Icon" src="${image_url}">
        <div class="info-header-text">
            <h1>${game_data["name"]}</h1>
            <p class="info-description">${game_data["description"]}</p>
            <div class="info-chips">
                <a href="/airspy/organizations/${game_data["organizationId"]}" class="info-chip">Author</a>
                <a href="https://airship.gg/g/${game_data["id"]}" class="info-chip" target="_blank" rel="noopener noreferrer">View on Airship</a>
                ${links}
                <span class="info-chip info-chip-badge ${isArchived ? "info-chip-warning" : ""}">${isArchived ? "Archived" : "Active"}</span>
            </div>
        </div>
    </div>

    <div class="info-stats-grid">
        <div class="info-stat"><span class="info-stat-label">Visibility</span><span class="info-stat-value">${game_data["visibility"]}</span></div>
        <div class="info-stat"><span class="info-stat-label">Platforms</span><span class="info-stat-value">${platforms}</span></div>
        <div class="info-stat"><span class="info-stat-label">Created</span><span class="info-stat-value">${formatDate(game_data["createdAt"])}</span></div>
        <div class="info-stat"><span class="info-stat-label">Last Updated</span><span class="info-stat-value">${formatDate(game_data["lastVersionUpdate"])}</span></div>
        <div class="info-stat"><span class="info-stat-label">Plays</span><span class="info-stat-value">${game_data["plays"]}</span></div>
        <div class="info-stat"><span class="info-stat-label">Favorites</span><span class="info-stat-value">${game_data["favorites"]}</span></div>
        <div class="info-stat"><span class="info-stat-label">Plays (24h)</span><span class="info-stat-value">${game_data["plays24h"]}</span></div>
        <div class="info-stat"><span class="info-stat-label">Unique Plays (24h)</span><span class="info-stat-value">${game_data["uniquePlays24h"]}</span></div>
    </div>

    <div class="info-meta-links">
        <a href="https://cnd.airship.gg/images/${game_data["iconImageId"]}" target="_blank" rel="noopener noreferrer">Icon</a>
        <a href="https://cnd.airship.gg/images/${game_data["logoImageId"]}" target="_blank" rel="noopener noreferrer">Logo</a>
    </div>
    `;
});
