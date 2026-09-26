import os
import requests

API_BASE = "https://api.digitalocean.com/v2"

def _headers():
    token = os.environ.get("DIGITALOCEAN_API_TOKEN")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}

def _get(path, params=None):
    headers = _headers()
    if headers is None:
        return None
    try:
        response = requests.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            return None
        return response.json()
    except requests.RequestException:
        return None

def is_configured():
    return _headers() is not None

def get_apps():
    data = _get("/apps")
    return data.get("apps", []) if data else []

def get_app_deployments(app_id, limit=10):
    data = _get(f"/apps/{app_id}/deployments", params={"per_page": limit})
    return data.get("deployments", []) if data else []

def get_app_bandwidth(app_id):
    data = _get(f"/apps/{app_id}/metrics/bandwidth_daily")
    if not data:
        return None
    apps = data.get("app_bandwidth_usage", {}).get("bandwidth_bytes_by_app_component", [])
    return apps

def get_app_run_logs(app_id, component_name=None, tail_lines=200):
    """Fetch the tail of the active deployment's live runtime logs. DO's log
    endpoint returns a URL to the actual log content rather than the log
    text itself, so this is a two-step fetch."""
    params = {"type": "RUN"}
    if component_name:
        params["component_name"] = component_name
    data = _get(f"/apps/{app_id}/deployments/active/logs", params=params)
    if not data:
        return None

    log_url = data.get("live_url") or data.get("url")
    if not log_url:
        historic = data.get("historic_logs") or []
        log_url = historic[0] if historic else None
    if not log_url:
        return None

    try:
        response = requests.get(log_url, timeout=10)
        if response.status_code != 200:
            return None
        lines = response.text.splitlines()
        return "\n".join(lines[-tail_lines:])
    except requests.RequestException:
        return None

def get_databases():
    data = _get("/databases")
    return data.get("databases", []) if data else []

def get_balance():
    return _get("/customers/my/balance")

def get_latest_invoice_items(limit=15):
    invoices = _get("/customers/my/invoices")
    if not invoices or not invoices.get("invoices"):
        return None, []

    latest = invoices["invoices"][0]
    detail = _get(f"/customers/my/invoices/{latest['invoice_uuid']}")
    items = detail.get("invoice_items", [])[:limit] if detail else []
    return latest, items

def get_live_database_stats():
    """Live size/connection stats for the database this site is actually
    connected to, queried directly rather than through DO's API (which only
    exposes cluster metrics via a separate Prometheus endpoint)."""
    from Site.code.database.main import get_db
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database())) AS size")
    size = cursor.fetchone()["size"]
    cursor.execute("SELECT count(*) AS count FROM pg_stat_activity WHERE datname = current_database()")
    connections = cursor.fetchone()["count"]
    cursor.execute("SHOW max_connections")
    max_connections = cursor.fetchone()["max_connections"]
    return {"size": size, "connections": connections, "max_connections": max_connections}
