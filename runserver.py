"""
This script runs the Site application using a development server.
"""

from subprocess import Popen
from os import environ
from Site import app
import os

os.system("taskkill /f /im cloudflared.exe 2>nul")
log_path = os.path.join(os.path.dirname(__file__), "cloudflared.log")
cmd = f'start /min cmd /c "cloudflared tunnel run --url http://localhost:5000 site > "{log_path}" 2>&1"'
Popen(cmd, shell=True)


if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5000'))
    except ValueError:
        PORT = 5000
    
    app.run(HOST, PORT)
