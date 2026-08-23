const searchInput = document.getElementById('search-input');
const suggestionsBox = document.getElementById('suggestions');

let dynamicMatches = [];

function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

async function handleTyping() {
    const query = searchInput.value.trim();

    if (query.length === 0) {
        suggestionsBox.style.display = 'none';
        dynamicMatches = [];
        return;
    }

    try {
        const response = await fetch(`/airspy/api/search?q=${encodeURIComponent(query)}`);
        dynamicMatches = await response.json();
        renderSuggestions(dynamicMatches);
    } catch (err) {
        console.error("Error retrieving auto-complete details:", err);
    }
}

function renderSuggestions(matches) {
    suggestionsBox.innerHTML = '';

    if (matches.length === 0) {
        suggestionsBox.style.display = 'none';
        return;
    }

    matches.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.textContent = item.title;

        div.addEventListener('click', () => {
            searchInput.value = item.title;
            suggestionsBox.style.display = 'none';
            window.location.href = item.url;
        });

        suggestionsBox.appendChild(div);
    });

    suggestionsBox.style.display = 'block';
}

searchInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
        const currentInputText = searchInput.value.trim().toLowerCase();

        const exactMatch = dynamicMatches.find(item => item.title.toLowerCase() === currentInputText);

        if (exactMatch) {
            window.location.href = exactMatch.url;
        } else if (dynamicMatches.length > 0) {
            const topSuggestion = dynamicMatches[0];
            searchInput.value = topSuggestion.title;

            suggestionsBox.style.display = 'none';
        } else {
            searchInput.style.borderColor = "#ea5455";
            setTimeout(() => searchInput.style.borderColor = "", 1000);
        }
    }
});

searchInput.addEventListener('input', debounce(handleTyping, 200));

document.addEventListener('click', function (e) {
    if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
        suggestionsBox.style.display = 'none';
    }
});
