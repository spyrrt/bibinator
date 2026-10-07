import configparser
from pathlib import Path

_cfg = configparser.ConfigParser()
_cfg.read(Path(__file__).parent.parent.parent / 'config.ini')

DB_NAME = _cfg['database']['name']
DB_CONFIG = {
    'host': _cfg['database']['host'],
    'port': int(_cfg.get('database', 'port', fallback='3306')),
    'user': _cfg['database']['user'],
    'password': _cfg['database']['password'],
    'database': DB_NAME,
    'allow_local_infile': True,
}

MODE = _cfg.get('setup', 'mode', fallback='original_files')
RUN_TESTS = _cfg.getboolean('setup', 'run_tests', fallback=True)
DROP_STAGING_TABLES = _cfg.getboolean('setup', 'drop_staging_tables', fallback=True)
EXPORT_FINAL_TABLES = _cfg.getboolean('setup', 'export_final_tables', fallback=True)
CREATE_BACKUP = _cfg.getboolean('setup', 'create_backup', fallback=True)