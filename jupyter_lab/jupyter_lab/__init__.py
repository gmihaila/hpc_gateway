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
START_OPEN_PORT = 9000
END_OPEN_PORT = 10000
DATABASE_NAME = 'database_jupyter_lab.db'
HOSTNAME = 'vis.acs.unt.edu'
CONDA_PATH = '/cm/shared/utils/PYTHON/ANACONDA/5.2'
PYTHON_PATH = '/cm/shared/utils/PYTHON/3.6.5'
JUPYTER_BIN_PATH = '/cm/shared/utils/PYTHON/3.6.5/bin/jupyter'
SESSION_LENGTH = 60

# CHECK DATABASE
if create_db(db_name=DATABASE_NAME):
    print(' * Databased checked!')
else:
    print(' * Database failed!\nQuit app...',  file=sys.stderr)
    sys.exit()

# FLASK APP
app = Flask(__name__)
from jupyter_lab import routes
