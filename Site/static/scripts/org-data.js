document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("org-info").innerHTML = `<h1>${org_data["name"]}</h1>
    <div class="outer-container-box">
        <img id="org-icon" alt="Organization Icon">
    </div>
    ${ org_data["description"]}<br>
    Created At: ${org_data["createdAt"]}<br>
    ${org_data["adminBanned"] ? "Admin has been banned" : "Admin is not banned"}
    `
    document.getElementById("org-icon").src = window.org_image;
});