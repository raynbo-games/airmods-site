import click
from flask import current_app, g
import psycopg
from psycopg.rows import dict_row

def get_db():
    if 'db' not in g:
        g.db = psycopg.connect(
            current_app.config['DATABASE_URL'],
            row_factory=dict_row
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('code/database/schemas/database.sql') as f:
        sql_script = f.read().decode('utf8')
        
    with db.cursor() as cursor:
        cursor.execute(sql_script)
    db.commit()

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('Initialized the managed PostgreSQL database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


# python -m flask --app Site init-db