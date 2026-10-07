import gzip
import subprocess
import time
import mysql.connector
import test_tables
import export_tables
from _config import DB_CONFIG, RUN_TESTS, EXPORT_FINAL_TABLES
from backup import BACKUP_FILE


def run():
    if not BACKUP_FILE.exists():
        raise FileNotFoundError(f'Backup file not found: {BACKUP_FILE}')

    start = time.time()
    print(f'Restoring from {BACKUP_FILE}...')

    host = DB_CONFIG['host']
    port = DB_CONFIG['port']
    user = DB_CONFIG['user']
    password = DB_CONFIG['password']

    with gzip.open(BACKUP_FILE, 'rb') as f:
        sql = f.read()

    result = subprocess.run(
        ['mysql', f'-h{host}', f'-P{port}', f'-u{user}', f'-p{password}'],
        input=sql, stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        raise RuntimeError(f'restore failed: {result.stderr.decode()}')

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        if RUN_TESTS:
            print('Running tests...')
            test_tables.run(cursor)

        if EXPORT_FINAL_TABLES:
            print('Exporting final tables...')
            export_tables.run(cursor)

        elapsed = time.time() - start
        print(f'\nSetup complete ! ({int(elapsed // 60)}m {elapsed % 60:.1f}s)')

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    run()
