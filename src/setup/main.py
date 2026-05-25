import mysql.connector
from _config import MODE, DB_CONFIG

if MODE == 'original_files':
    import full_pipeline
    full_pipeline.run()
elif MODE == 'backup':
    import backup_pipeline
    backup_pipeline.run()
elif MODE == 'validate':
    import test_tables
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        test_tables.run(cursor)
    finally:
        cursor.close()
        conn.close()
else:
    print(f'\033[31mUnknown mode: {MODE}\033[0m')
    print('Valid modes: original_files, backup, validate')
    exit(1)
