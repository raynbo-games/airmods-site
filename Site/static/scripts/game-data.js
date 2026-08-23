document.addEventListener("DOMContentLoaded", () => {
    const links = "";
    for (let [key, value] in Object.entries(game_data["links"])) {
        links += `<a href="${value}">${key}</a>\n`;
    }
    const platforms = game_data["platforms"].join(", ");

    document.getElementById("game-info").innerHTML = `<h1>${game_data["name"]}</h1>
    <div class="outer-container-box">
        <img id="game-icon" alt="Game Icon">
    </div>
    <p>${ game_data["description"]}</p>

    <p><a href="/airspy/organizations/${game_data["organizationId"]}">Author</a>, <a href="https://airship.gg/g/${game_data["id"]}">Game Link</a></p>
    Images: <a href="https://cnd.airship.gg/images/${game_data["iconImageId"]}">Icon</a>, <a href="https://cnd.airship.gg/images/${game_data["logoImageId"]}">Logo</a><br>
    <p>
    Visiblility: ${game_data["visibility"]}<br>
    Platforms: ${game_data["platforms"]}<br>
    Created At: ${game_data["createdAt"]}<br>
    Last Updated At: ${game_data["lastVersionUpdate"]}<br>
    ${game_data["archivedAt"] ? "Game is archived" : "Game is not archived"}<br>
    Links: ${links}<br>
    Plays: ${game_data["plays"]}<br>
    Favorites: ${game_data["favorites"]}<br>
    Plays 24h: ${game_data["plays24h"]}<br>
    Unique Plays 24h: ${game_data["uniquePlays24h"]}<br>
    </p>
    `

    document.getElementById("game-icon").src = window.game_image;
});