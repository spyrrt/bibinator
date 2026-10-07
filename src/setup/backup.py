import gzip
import subprocess
import mysql.connector
from pathlib import Path
from _config import DB_NAME, DB_CONFIG

BACKUP_DIR = Path(__file__).parent.parent.parent / 'data' / 'backup'
BACKUP_FILE = BACKUP_DIR / f'{DB_NAME}.sql.gz'

TABLE_ORDER = [
    'FOR_LOOKUP',
    'BEST_SUBJECT_AREA_LOOKUP',
    'AUTHOR_LOOKUP',
    'ARTICLES',
    'CONF_RANKING',
    'MAG_RANKING',
    'CONF_ARTICLE_INFO',
    'MAG_ARTICLE_INFO',
    'ARTICLE_AUTHORS',
]


def _get_ordered_tables():
    order_list = ', '.join(f"'{t}'" for t in TABLE_ORDER)
    sql = (
        f"SELECT GROUP_CONCAT(table_name "
        f"ORDER BY FIELD(table_name, {order_list}) "
        f"SEPARATOR ' ') "
        f"FROM information_schema.tables "
        f"WHERE table_schema = '{DB_NAME}' "
        f"AND table_name IN ({order_list})"
    )
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return result.split()


def _is_mysql_client():
    result = subprocess.run(['mysqldump', '--version'], capture_output=True, text=True)
    output = result.stdout + result.stderr
    return 'MariaDB' not in output


def run():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    host = DB_CONFIG['host']
    port = DB_CONFIG['port']
    user = DB_CONFIG['user']
    password = DB_CONFIG['password']

    tables = _get_ordered_tables()

    args = [
        'mysqldump', f'-h{host}', f'-P{port}', f'-u{user}', f'-p{password}',
    ]
    if _is_mysql_client():
        args.append('--column-statistics=0')
    args += [DB_NAME, '--tables'] + tables

    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        raise RuntimeError(f'mysqldump failed: {result.stderr.decode()}')

    db_header = (
        f'DROP DATABASE IF EXISTS `{DB_NAME}`;\n'
        f'CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n'
        f'USE `{DB_NAME}`;\n\n'
    ).encode()

    with gzip.open(BACKUP_FILE, 'wb') as f:
        f.write(db_header + result.stdout)

    size_mb = BACKUP_FILE.stat().st_size / 1024 / 1024
    print(f'  Backup saved to {BACKUP_FILE} ({size_mb:.1f}MB)')


if __name__ == '__main__':
    run()
