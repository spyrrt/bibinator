import subprocess
import sys
from _config import APP_MODE, APP_PORT

if APP_MODE == 'run':
    try:
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', 'app.py', '--server.port', str(APP_PORT)])
    except KeyboardInterrupt:
        pass
elif APP_MODE == 'test_queries':
    import test_queries
    test_queries.run()
else:
    print(f'\033[31mUnknown mode: {APP_MODE}\033[0m')
    print('Valid modes: run, test_queries')
    exit(1)
