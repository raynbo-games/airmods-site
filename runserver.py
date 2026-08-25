"""
This script runs the Site application using a development server.
"""

from subprocess import Popen
from os import environ
from Site import app

if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '8080'))
    except ValueError:
        PORT = 8080
    
    app.run(HOST, PORT)
