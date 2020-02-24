#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Python Flask Server to automate Jupyter Lab port forward on HPC cluster.
Start the server with the 'run()' method

(C) 2020 George Mihaila
email georgemihaila@my.unt.edu
"""

import time
from datetime import datetime
from multiprocessing import Process, Pipe
from flask import render_template, redirect, url_for, request
# LOCAL IMPORTS
from jupyter_lab import app, DATABASE_NAME, HOSTNAME, CONDA_PATH, PYTHON_PATH, JUPYTER_BIN_PATH, SESSION_LENGTH
from helper_functions import logger,kill_pid
from sqlite_database import from_db, add_db
from jupyter_instance import jupyter_run



@app.route('/', methods=['GET', 'POST'])
def home():
    '''Home page used to login. Retrieve user and pass with @app.route methods.
    Steps to follow:
        - CHECK IF USER WAS EVER LOGGED IN. IF NOT START USER FROM SCRATCH.
        - ADD USER IN DATABASE WITH RUNNING INSTANCE.
        - FOR RETURNING USER CHECK THE INSTANCE STATUS.
        - FOR INITIATED INSTANCES AVOID RE-RUNNING PROCESSES.
        - KEEP CHECKING STATE FOR 1 MINUT. IF NO CHANGE CONSIDER INSTANCE ENDED AND RE-START.
        - IF STATE CHANGES - RE-FRESH CONNECITON FROM GATEWAY TO TALON.
    '''

    request_ip = str(request.remote_addr)
    request_method = request.method
    error = None

    if request_method == 'POST':
        user_id = request.form['username']
        user_credential = request.form['password']

        logger(user='root', message='Request method: %s user: %s ip: %s'%(request_method, user_id, request_ip), level='WARNING')

        # CHECK IF USER ALREADY INITIATED
        user_log = from_db(db_name=DATABASE_NAME, user=user_id)

        # USER NEVER LOGGED IN
        if user_log is None:
            # UPDATE USER IN DATABASE
            add_db(db_name=DATABASE_NAME,
                   user=user_id,
                   last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   local_port=0,
                   talon_port=0,
                   login_node=HOSTNAME,
                   pid_session=0,
                   state_session='initiated')

            # SEPARATE PYTHON PROCESS
            # CREATE SEPARATE PROCESS PIPELINE COMMUNICATION
            parent_conn, child_conn = Pipe()
            # START SEPARATE PYTHON PROCESS
            python_process = Process(target=jupyter_run, args=(parent_conn,
                                                                user_id, user_credential,
                                                                HOSTNAME,
                                                                CONDA_PATH,
                                                                PYTHON_PATH,
                                                                JUPYTER_BIN_PATH,
                                                                SESSION_LENGTH))
            python_process.start()

            # expect communication from instance pipe communicaiton
            process_message = child_conn.recv()
            state_session, jupyter_port = process_message.split()

            # CHECK SESSION STATE
            if state_session == 'ended':
                if jupyter_port == 'None':
                    # CONNECTION FAILED
                    logger(user=user_id, message='SERVER ERROR!', level='ERROR')
                    return render_template('login.html', error='Server error! Please report to HPC-Admin!')
                else:
                    # CONNECTION FAILED
                    logger(user=user_id, message='INVALID CREDENTIAL', level='ERROR')
                    return render_template('login.html', error='Invalid Credentials. Please try again.')
            else:
                # CONNECTION SUCCESSFULL
                ide_link = "http://hpc-gateway.hpc.unt.edu:%s"%(jupyter_port)
                time.sleep(5)
                logger(user=user_id, message='FORWARDING LOGIN PAGE TO JUPYTER LAB!', level='INFO')
                return redirect(ide_link)


        # USER IN PROCESS OF LOGGING IN
        elif user_log['state_session'] == 'initiated':
            # FAIL TO REDIRECT
            logger(user='root', message='USER %s ALREADY INITIATED!'%(user_id), level='WARNING')
            return render_template('login.html', error='User Already Initiated!')

        # JUPYTER SESSION RUNNING OR ENDED
        elif (user_log['state_session'] == 'running') or (user_log['state_session'] == 'ended'):
            # KILL PREVIOUS PID IF EXISTING
            if user_log['pid_session']!=0: kill_pid(pid=user_log['pid_session'])
            # UPDATE USER IN DATABASE
            add_db(db_name=DATABASE_NAME,
                   user=user_id,
                   last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   local_port=0,
                   talon_port=0,
                   login_node=HOSTNAME,
                   pid_session=0,
                   state_session='initiated')

            # SEPARATE PYTHON PROCESS
            # CREATE SEPARATE PROCESS PIPELINE COMMUNICATION
            parent_conn, child_conn = Pipe()
            # START SEPARATE PYTHON PROCESS
            python_process = Process(target=jupyter_run, args=(parent_conn,
                                                                user_id, user_credential,
                                                                HOSTNAME,
                                                                CONDA_PATH,
                                                                PYTHON_PATH,
                                                                JUPYTER_BIN_PATH,
                                                                SESSION_LENGTH))
            python_process.start()

            # expect communication from instance pipe communicaiton
            process_message = child_conn.recv()
            state_session, jupyter_port = process_message.split()

            # CHECK SESSION STATE
            if state_session == 'ended':
                if jupyter_port == 'None':
                    # CONNECTION FAILED
                    logger(user=user_id, message='SERVER ERROR!', level='ERROR')
                    return render_template('login.html', error='Server error! Please report to HPC-Admin!')
                else:
                    # CONNECTION FAILED
                    logger(user=user_id, message='INVALID CREDENTIAL', level='ERROR')
                    return render_template('login.html', error='Invalid Credentials. Please try again.')
            else:
                # CONNECTION SUCCESSFULL
                ide_link = "http://jupyterlab.hpc.unt.edu:%s"%(jupyter_port)
                time.sleep(5)
                logger(user=user_id, message='FORWARDING LOGIN PAGE TO JUPYTER LAB!', level='INFO')
                return redirect(ide_link)


    return render_template('login.html', login='login')
