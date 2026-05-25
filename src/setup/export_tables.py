import csv
import mysql.connector
from pathlib import Path
from _config import DB_CONFIG

OUTPUT_DIR = Path(__file__).parent.parent.parent / 'data' / 'final_tables'

FINAL_TABLES = [
    'AUTHOR_LOOKUP',
    'ARTICLES',
    'FOR_LOOKUP',
    'BEST_SUBJECT_AREA_LOOKUP',
    'CONF_RANKING',
    'MAG_RANKING',
    'CONF_ARTICLE_INFO',
    'MAG_ARTICLE_INFO',
    'ARTICLE_AUTHORS',
]


def run(cursor):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for table in FINAL_TABLES:
        cursor.execute(f'SELECT * FROM `{table}`')
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        with open(OUTPUT_DIR / f'{table}.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerows(rows)


if __name__ == '__main__':
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        run(cursor)
    finally:
        cursor.close()
        conn.close()