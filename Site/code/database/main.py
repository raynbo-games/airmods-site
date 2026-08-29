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

def get_matching_row(table_name, properties_dict, multiple=False):
    db = get_db()
    cursor = db.cursor()
    
    conditions = [f'"{col}" = %s' for col in properties_dict.keys()]
    where_clause = " AND ".join(conditions)
    
    query = f'SELECT * FROM "{table_name}" WHERE {where_clause}'

    if multiple: return cursor.execute(query, list(properties_dict.values())).fetchall()
    return cursor.execute(query, list(properties_dict.values())).fetchone()

def get_property_value(table_name, property_key):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f'SELECT "{property_key}" FROM "{table_name}"')
    rows = cursor.fetchall()
    return [row[property_key] for row in rows]

def get_multiple_property_values(table_name, *property_keys):
    db = get_db()
    cursor = db.cursor()
    query = ", ".join([f'"{item}"' for item in property_keys])
    cursor.execute(f'SELECT {query} FROM "{table_name}"')
    rows = cursor.fetchall()
    return [{key.strip('"'): value for key, value in row.items()} for row in rows]