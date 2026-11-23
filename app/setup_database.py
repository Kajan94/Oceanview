"""Installation locale des données marines originales incluses dans le dépôt."""
import hashlib
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import click
import mysql.connector
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app.models.database import connect_database


ARCHIVE_SHA256 = 'c41546501508d1d8bfd3bea90bf014035c0c7622cb8e1182bf2ca97db998f7fb'
TABLES = (
    ('variable', 'variables', 3),
    ('localisation', 'localisations', 202201),
    ('mesure', 'mesures', 17421439),
)


def included_archive():
    path = Path(__file__).resolve().parent.parent / 'data' / 'oceanview.zip'
    if not path.is_file():
        raise click.ClickException('Archive data/oceanview.zip absente. Téléchargez le dépôt complet indiqué dans le README.')
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != ARCHIVE_SHA256:
            raise click.ClickException('Archive incomplète ou pointeur Git LFS : récupérez le fichier complet indiqué dans le README.')
    return path


def import_table(archive, cursor, table, label, expected):
    entry = f'BD_oceanview/oceanview_{label}_20261120_v2.sql'
    prefix = f'INSERT INTO {table} VALUES'
    batch = []
    count = 0
    with archive.open(entry) as source:
        for raw_line in source:
            line = raw_line.decode('utf-8').rstrip('\n')
            if not line.startswith(prefix + '(') or not line.endswith(');'):
                raise click.ClickException(f'Format inattendu dans la table {table}.')
            batch.append(line[len(prefix):-1])
            count += 1
            if len(batch) == 5000:
                cursor.execute(prefix + ','.join(batch))
                batch.clear()
            if count % 1000000 == 0:
                click.echo(f'{table} : {count:,} / {expected:,} lignes'.replace(',', ' '))
        if batch:
            cursor.execute(prefix + ','.join(batch))
    if count != expected:
        raise click.ClickException(f'Table {table} incomplète : {count} lignes, {expected} attendues.')
    click.echo(f'{table} : {count:,} lignes importées'.replace(',', ' '))


@click.command('init-db')
@with_appcontext
def init_database():
    """Reconstitue la base complète dans une base MySQL vide."""
    path = included_archive()
    schema = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
    try:
        with connect_database() as connection, connection.cursor() as cursor:
            cursor.execute('SHOW FULL TABLES')
            if cursor.fetchall():
                raise click.ClickException(
                    'Cette base contient déjà des tables. Utilisez une nouvelle base vide pour importer les données ; '
                    'pour relancer le site, exécutez seulement python run.py.'
                )
            for statement in schema.split(';'):
                if statement.strip():
                    cursor.execute(statement)
            try:
                with ZipFile(path) as archive:
                    for table, label, expected in TABLES:
                        import_table(archive, cursor, table, label, expected)
                for table, _, expected in TABLES:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    if cursor.fetchone()[0] != expected:
                        raise click.ClickException(f'Le contrôle final de {table} a échoué.')
                connection.commit()
            except Exception:
                connection.rollback()
                raise
    except mysql.connector.Error as error:
        raise click.ClickException(
            f'Initialisation MySQL impossible ({error.errno}). Vérifiez la connexion et utilisez une base vide.'
        ) from error
    except (BadZipFile, KeyError) as error:
        raise click.ClickException('Archive de données invalide ou incomplète.') from error
    click.echo('Base prête : 17 421 439 mesures originales, 202 201 positions et 3 indicateurs. Aucun compte personnel importé.')


@click.command('create-admin')
@click.option('--email', required=True, help='Adresse du nouveau compte administrateur local.')
@with_appcontext
def create_admin(email):
    """Crée un administrateur local après l'import des données."""
    password = click.prompt('Mot de passe administrateur', hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        raise click.ClickException('Utilisez au moins 8 caractères.')
    try:
        with connect_database() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO utilisateur (Nom_Utilisateur, Email, Role, Mot_de_Passe) VALUES (%s, %s, 'Admin', %s)",
                ('Administration locale', email, generate_password_hash(password)),
            )
            connection.commit()
    except mysql.connector.Error as error:
        raise click.ClickException(
            f'Création impossible ({error.errno}). Vérifiez la connexion, l’initialisation et que cette adresse est encore inutilisée.'
        ) from error
    click.echo('Compte administrateur local créé.')
