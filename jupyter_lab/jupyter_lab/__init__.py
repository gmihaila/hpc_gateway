#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Python Flask Server to automate Jupyter Lab port forward on HPC cluster.
Start the server with the 'run()' method

(C) 2020 George Mihaila
email georgemihaila@my.unt.edu
"""

import os
import sys
from flask import Flask
from sqlite_database import create_db

# ENVIROMENT VARIABLES
DATABASE_NAME = os.environ['DATABASE_NAME']
HOSTNAME = os.environ['HOSTNAME']
CONDA_PATH = os.environ['CONDA_PATH']
PYTHON_PATH = os.environ['PYTHON_PATH']
JUPYTER_BIN_PATH = os.environ['JUPYTER_BIN_PATH']
SESSION_LENGTH = os.environ['SESSION_LENGTH']

# CHECK DATABASE
if create_db(db_name=DATABASE_NAME):
    print(' * Databased checked!')
else:
    print(' * Database failed!\nQuit app...',  file=sys.stderr)
    sys.exit()

# FLASK APP
app = Flask(__name__)
from jupyter_lab import routes
