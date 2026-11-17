from datetime import date
from math import cos, exp, pi, sin, tanh
from pathlib import Path

import click
import mysql.connector
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app.models.database import connect_database


POSITIONS = [
    (49.4, -4.2), (49.6, -2.1), (50.0, -0.5), (50.3, 0.9),
    (43.7, -6.0), (44.7, -4.9), (45.2, -3.7), (46.2, -5.0),
    (41.5, 4.2), (42.2, 5.5), (41.2, 8.1), (39.7, 10.3),
    (53.0, -12.4), (54.0, -11.0), (55.2, -13.2), (55.6, -8.2),
]
# Bandes de points fictifs en mer : Manche, golfe de Gascogne,
# Méditerranée occidentale, Atlantique et Baltique.
# Les 16 positions initiales restent en tête pour conserver leurs identifiants.
SEA_ROWS = [
    (49.3, -5.4, -2.6), (49.7, -5.4, -1.0),
    (50.1, -4.6, 0.6), (50.5, -1.0, 1.4),
    (43.9, -9.0, -3.0), (44.3, -9.0, -2.2),
    (44.7, -9.0, -2.2), (45.1, -9.0, -2.2),
    (45.5, -9.0, -2.2), (45.9, -9.0, -2.6),
    (46.3, -9.0, -3.0), (46.7, -9.0, -3.8),
    (47.1, -9.0, -4.6), (47.5, -9.0, -5.4),
    (38.3, 4.2, 7.4), (38.7, 4.2, 7.4),
    (39.1, 4.2, 7.4), (39.5, 4.2, 7.4),
    (39.9, 4.2, 7.4), (40.3, 4.2, 7.4),
    (40.7, 4.2, 7.4), (41.1, 3.8, 7.0),
    (41.5, 3.8, 7.0), (41.9, 4.2, 7.0),
    (42.3, 4.6, 7.0), (42.7, 5.0, 7.0),
    (52.3, -16.2, -12.6), (52.7, -16.2, -12.6),
    (53.1, -16.2, -12.6), (53.5, -16.2, -12.6),
    (53.9, -16.2, -12.6), (54.3, -16.2, -12.6),
    (55.5, 16.2, 19.0), (55.9, 17.0, 19.8),
    (56.3, 17.4, 20.2), (56.7, 18.2, 20.2),
    (57.1, 18.6, 20.6), (57.5, 19.4, 21.0),
    (57.9, 19.8, 21.4),
]
for latitude, west, east in SEA_ROWS:
    for step in range(round((east - west) / 0.4) + 1):
        position = (latitude, round(west + step * 0.4, 2))
        if position not in POSITIONS:
            POSITIONS.append(position)

VARIABLES = [(1, 'SST'), (2, 'SSS'), (3, 'Chl-a')]


def demo_measurements():
    rows = []
    for month in range(1, 13):
        season = cos((month - 8) * pi / 6)
        for location, (latitude, longitude) in enumerate(POSITIONS, 1):
            # Champs synthétiques continus : nord plus froid, Baltique moins
            # salée et concentrations de chlorophylle près de la Manche.
            baltic = exp(-((latitude - 57) ** 2 / 14 + (longitude - 20) ** 2 / 25))
            channel = exp(-((latitude - 49.7) ** 2 / 3 + (longitude + 2) ** 2 / 8))
            biscay = exp(-((latitude - 45) ** 2 / 4 + (longitude + 3) ** 2 / 6))
            values = (
                24 - (latitude - 38) * 0.8 + 5 * season + sin(longitude * pi / 12),
                36 + 1.8 * tanh((longitude - 2) / 6) - 24 * baltic + 0.4 * season,
                0.15 + 3.4 * channel + 2.0 * biscay + 0.7 * baltic + 0.45 * (1 - season),
            )
            for variable, value in enumerate(values, 1):
                # Les requêtes historiques échantillonnent par ID de mesure.
                rows.append((100 * (len(rows) + 1), variable, location, date(2025, month, 1), round(value, 2)))
    return rows


@click.command('init-demo')
@click.option('--admin-email', help='Créer un compte administrateur de démonstration.')
@with_appcontext
def init_demo(admin_email):
    """Initialise une base MySQL dédiée à la démonstration."""
    if not current_app.config['DB_NAME'].endswith('_demo'):
        raise click.ClickException('Utilisez une base dédiée dont le nom se termine par _demo.')

    admin_password = None
    if admin_email:
        admin_password = click.prompt(
            'Mot de passe administrateur',
            hide_input=True,
            confirmation_prompt='Confirme le mot de passe administrateur',
        )
        if len(admin_password) < 8:
            raise click.ClickException('Utilisez au moins 8 caractères.')

    schema = Path(__file__).with_name('schema_demo.sql').read_text(encoding='utf-8')
    try:
        with connect_database() as connection, connection.cursor() as cursor:
            cursor.execute(schema)
            while cursor.nextset():
                pass
            cursor.executemany('INSERT IGNORE INTO variable VALUES (%s, %s)', VARIABLES)
            cursor.executemany('INSERT IGNORE INTO localisation VALUES (%s, %s, %s)', [
                (index, lat, lon) for index, (lat, lon) in enumerate(POSITIONS, 1)
            ])
            # Une nouvelle exécution actualise les mesures fictives existantes.
            # Les comptes, favoris, avis et journaux restent inchangés.
            rows = demo_measurements()
            cursor.executemany(
                'INSERT INTO mesure VALUES (%s, %s, %s, %s, %s) AS demo '
                'ON DUPLICATE KEY UPDATE ID_Variable = demo.ID_Variable, '
                'ID_Localisation = demo.ID_Localisation, '
                'Jour_Opti = demo.Jour_Opti, Valeur = demo.Valeur',
                rows,
            )
            if admin_email:
                cursor.execute(
                    "INSERT INTO utilisateur (Nom_Utilisateur, Email, Role, Mot_de_Passe) VALUES (%s, %s, 'Admin', %s)",
                    ('Administration démo', admin_email, generate_password_hash(admin_password)),
                )
            connection.commit()
    except mysql.connector.Error as error:
        raise click.ClickException(f'Initialisation MySQL impossible ({error.errno}). Vérifiez la base et la configuration locale.') from error

    click.echo(f'La base OcéanView est prête : {len(POSITIONS)} positions et {len(rows)} mesures fictives actualisées.')
