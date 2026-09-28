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

def update_db():
    db = get_db()

    with current_app.open_resource('code/database/schemas/update.sql') as f:
        sql_script = f.read().decode('utf8')
        
    with db.cursor() as cursor:
        cursor.execute(sql_script)
    db.commit()

def wipe_db():
    db = get_db()

    with current_app.open_resource('code/database/schemas/wipe.sql') as f:
        sql_script = f.read().decode('utf8')
        
    with db.cursor() as cursor:
        cursor.execute(sql_script)
    db.commit()

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('Initialized the PostgreSQL database.')

@click.command('update-db')
def update_db_command():
    update_db()
    init_db()
    click.echo('Updated the PostgreSQL database.')

@click.command('wipe-db')
def wipe_db_command():
    wipe_db()
    init_db()
    click.echo('Wiped the PostgreSQL database.')

@click.command('set-user-auth')
@click.option('--username', help='username of the user.')
@click.option('--auth', default=0, help='auth level (0-4).')
def set_user_auth_command(username, auth):
    if not username:
        return click.echo(f'No username specified')

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(f'UPDATE "user" SET "auth" = %s WHERE "username" = %s;', (auth, username))
        db.commit()
        click.echo(f"Successfully updated auth to {auth} for user: {username}")
    except psycopg.DatabaseError as error:
        db.rollback()
        click.echo(f"Database error occurred: {error}")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(update_db_command)
    app.cli.add_command(set_user_auth_command)
    app.cli.add_command(wipe_db_command)

    from Site.code.airspy.database import reset_airspy_db_command, fix_airspy_data_command
    app.cli.add_command(reset_airspy_db_command)
    app.cli.add_command(fix_airspy_data_command)

    from Site.code.airspy.compile import recompile_airspy_stats_command
    app.cli.add_command(recompile_airspy_stats_command)

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