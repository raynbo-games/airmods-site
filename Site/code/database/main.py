import sqlite3, click, json
from flask import current_app, g
from datetime import datetime

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('code/database/schemas/database.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('Initialized the database.')

timestamp_converter = lambda v: datetime.fromisoformat(v.decode().replace('Z', '+00:00'))

sqlite3.register_converter(
    "timestamp", timestamp_converter
)

sqlite3.register_converter("JSON", json.loads)

def convert_to_timestamp(v):
    if not v:
        return None
    return timestamp_converter(v.encode())

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    #python -m flask --app Site init-db