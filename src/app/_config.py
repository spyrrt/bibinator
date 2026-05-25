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
}

APP_PORT = int(_cfg.get('app', 'port', fallback='8501'))
APP_MODE = _cfg.get('app', 'mode', fallback='run')
