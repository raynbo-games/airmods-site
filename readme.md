# Raynbo Games Site

This is an Archived project for Raynbo Games' old site, before the Airship platform by Easy Games was discontinued.

In this project, users could view stats for games on the Airship platform over time and visualize analytics data in line charts using Airspy.
Airmods was also managed via this site; however, Airship was discontinued before Airmods was finished.

AI was utilized in this project for the creation of documentation and basic utilities.

## Feature areas

Each area is a Flask blueprint under `Site/code/`, paired with its own `database.py` for DB access:

- **root** (`main/`) — home page, ToS redirect, privacy policy.
- **airspy** (`airspy/`) — polls the Airship API on a scheduler, stores tick-by-tick player count/play stats per game and organization, and renders dashboards with charts (day/month/year, all-time-highs).
- **airmods** (`airmods/`) — placeholder landing page.
- **auth** (`auth/`) — Google OAuth login, account creation, and auth-level gating (`BANNED`/`USER`/`MODERATOR`/`ADMIN`/`DEVELOPER`/`OWNER`/`SYSTEM`).
- **admin** (`admin/`) — user management, audit log, Discord webhook/automod configuration.
- **community** (`community/`) — suggestion board with voting, threaded comments, moderation, an automod review queue, and an inbox for notifications.
- **roadmap** (`roadmap/`) — draggable roadmap boxes connected by arrows, each with its own vote/comment thread.

Shared infrastructure lives in `Site/code/database/` (Postgres connection + generic row helpers, CDN upload/URL helpers), `Site/code/context.py` (global template context + error handling), `Site/code/config.py` (Airspy tuning constants), and `Site/code/tasks.py` (APScheduler job registration).

## Setup

1. Activate the virtual environment:
   ```
   ./env/Scripts/Activate.ps1
   ```
2. Install dependencies: `pip install -r requirements.txt`
3. Set the required environment variables (a `.env` file is loaded automatically):
   - `DATABASE_URL` — Postgres connection string.
   - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` — Google login.
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — DigitalOcean Spaces (CDN) credentials.
   - `AIRSHIP_AUTHORIZATION` — bearer token for the Airship API.
   - `SERVER_HOST`, `SERVER_PORT` — optional, default to `localhost:8080` (used by `runserver.py`).
4. Initialize the database: `python -m flask --app Site init-db`
5. Run the dev server: `python runserver.py`

### Database CLI commands

| Command | Effect |
|---|---|
| `python -m flask --app Site init-db` | Create tables from `code/database/schemas/database.sql`. |
| `python -m flask --app Site update-db` | Apply `code/database/schemas/update.sql`, then re-run `init-db`. |
| `python -m flask --app Site wipe-db` | Drop all data via `code/database/schemas/wipe.sql`, then re-run `init-db`. |
| `python -m flask --app Site fix-airspy-data` | Fixes data errors |
| `python -m flask --app Site recompile-airspy-stats` | Rebuild organization and global stats from raw game data (same as the admin panel button). |
| `python -m flask --app Site set-user-auth --username USER_NAME --auth AUTH_LEVEL` | Set a user's auth level directly. |
| `python -m flask --app Site reset-airspy-db [--yes]` | Delete all tracked Airspy games/organizations/tick data. |

## Utility modules

- `Site/code/database/main.py` — `get_db()`/`init_app()` for the Postgres connection and CLI registration, plus generic helpers used across every blueprint: `get_matching_row`, `get_property_value`, `get_multiple_property_values`.
- `Site/code/database/cdn.py` — uploads/serves images through DigitalOcean Spaces (`upload_to_spaces`, `get_image_cdn_url`) and builds CDN URLs for bundled static assets (`cdn`, `cdn_script`, `cdn_style`, `cdn_image`).
- `Site/code/airspy/airship_urls.py` — builds and requests Airship API/CDN URLs (`request_games`, `request_game_id`, `request_image`, etc).
- `Site/code/airspy/utility.py` — `bucket_series` downsamples a tick-resolution series into fixed buckets; `get_dashboard_data` turns raw stats into chart-ready series plus all-time-high data.
- `Site/code/community/webhook.py` — Discord webhook notifications (`send_discord_notification`) and automod word-list checks (`check_automod`), both driven by the `community_config` JSON row.

## Contributing

- Match the blueprint pattern: routes/view logic in `main.py`, all SQL in `database.py`.
- Python locals and function names are `snake_case`. The one exception: a local variable that mirrors a field name from the Airship API or a database column (e.g. `liveStats`, `gameStats`) keeps that field's original casing for traceability — never rename those.
- Database columns and JSON keys are `camelCase`, matching either the Postgres schema or the external Airship API. Don't rename them.
- JS locals and function names are `camelCase`.
- Don't write inline comments explaining individual lines. Only add a short one-line or two-line docstring/comment directly above a function definition, and only when its behavior isn't obvious from its name and signature.
- Vendored third-party files (jQuery, Bootstrap, Chart.js, Modernizr, Respond, `npm.js`) under `Site/static/scripts/` are untouched dependencies — don't restyle or reformat them.
