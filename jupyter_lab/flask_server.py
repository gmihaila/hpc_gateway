#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Python Flask Server to automate Jupyter Lab port forward on HPC cluster.
Start the server with the 'run()' method

(C) 2020 George Mihaila
email georgemihaila@my.unt.edu
"""
from flask import Flask, render_template, redirect, url_for, request
import pexpect
import sys
from io import StringIO
from multiprocessing import Process, Pipe
import os
import time
from datetime import datetime
import sqlite3
import socket
from contextlib import closing

# GLOBAL VARIABLES
LOGIN_NODE = 'vis.acs.unt.edu'
DATE_TEMPLATE = '%Y-%m-%d %H:%M:%S'
SESSION_TIME = 60  # seconds
DB_NAME = 'jupyter_talon_usage.db'
# if not activity detected - end jupyter instance
# if user re-logs in timeframe it will reset idle time
JUPYTER_HPC_TIMEOUT = 60    #seconds 15 default


def find_free_port():
    """Find available port

    Return:
        available_port: Available random port. Int type.
    """

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        available_port = s.getsockname()[1]
        return available_port


def logger(user, message, level, fname='logs.log', verbose=True, extra_log=True):
    """Logging function

    Args:
      user: user id
      message: text needed logged
      level: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
      fname: file name to save all logs
      verbose: if print to stdou
      extra_log: create 'logs/' and write individual logs for each user

    Source: https://docs.python.org/2/howto/logging.html
    """

    # get time of log
    time_log = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # check input arguments types
    assert level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']
    assert str(user) and str(message)
    # create log line from message and date
    line = '%s %s %s %s' % (time_log, str(user), level, str(message))
    # print to stdout if veborse
    if verbose:
        print(line)
    # append to main log file
    with open(fname, 'a') as f:
        f.write(line + '\n')
    if extra_log:
        # create if folder does not exist
        if os.path.isdir('logs') is False:
            os.mkdir('logs')
        # append to user log file
        with open('logs/%s.log' % user, 'a') as f:
            f.write(line + '\n')
    return


def kill_pid(pid):
    """Kill any running processes based on PID.

    Args:
        pid: pid of process that will be killed.
    Return:
        False or True if was killed or not
    """
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def create_db(db_name):
    '''Create new Database if it does not exist.

    Args:
        db_name: Database name.
    '''

    try:
        # CHECK IF DB EXISTS OR NOT
        if not os.path.isfile(db_name):
            # DB DOES NOT EXIST - CREATE DB
            conn = sqlite3.connect(db_name)
            # DB CONNECTION
            c = conn.cursor()
            # CREATE TABLE IN DB
            c.execute('''CREATE TABLE jupyter_talon
                  (euid, first_login, last_login, local_port, talon_port, login_node, count_logins, pid_session , state_session)''')
            # SAVE (COMMIT) THE CHANGES
            conn.commit()
            # CLOSE CONNECITON
            conn.close()

        return True
    except Exception as e:
        logger(user='root', message='DB FAILED! %s' % str(e), level='ERROR')
        return False


def add_db(db_name, euid, last_login, local_port, talon_port, login_node, pid_session, state_session):
    '''Add instance in database or create database if it does not exist.
    Columns: 'euid', 'first_login', 'last_login', 'local_port', 'talon_port',
        'login_node', 'count_logins', 'pid_session', 'state_session'.

    Args:
        db_name: Database name.
        euid: User id.
        last_login: Last login date recorded
        local_port: Port on local VM gateway used to forward.
        talon_port: Port on HPC needed to forward.
        login_node: Hostname on HPC.
        pid_session: Pid of running process that does ssh tunneling.
        state_session: State of the process:
            'initiated' [login is started]
            'running'   [login is successfull]
            'ended'     [session ended]
    '''
    # DB CONNECTION
    conn = None
    # DB CURSOR
    c = None
    try:

        # CHECK IF DB EXISTS OR NOT
        if not os.path.isfile(db_name):
            # DB DOES NOT EXIST - CREATE DB
            conn = sqlite3.connect(db_name)
            # DB CONNECTION
            c = conn.cursor()
            # CREATE TABLE IN DB
            c.execute('''CREATE TABLE jupyter_talon
                  (euid, first_login, last_login, local_port, talon_port, login_node, count_logins, pid_session , state_session)''')
        else:
            # DB EXISTS - JUST ESTABLISH CONNECTION
            # CONNECT TO DB
            conn = sqlite3.connect(db_name)
            # DB CONNECTION
            c = conn.cursor()

        # CHECK IF EUID ALREADY EXISTS
        euids = list(
            c.execute('SELECT euid FROM jupyter_talon ORDER BY euid').fetchall())
        if (euid,) in euids:
            # EUID ALREADY IN DB
            # GRAB NUMBER OF LOGINS
            count_logins = (c.execute(
                'SELECT count_logins FROM jupyter_talon WHERE euid=?', (euid,)).fetchall())[0][0]
            # ONLY COUNT AS LOGIN WHEN RUNNING
            if state_session == 'running':
                # INCREMENT LOGINS
                count_logins += 1
            # INCREMENT count_login
            c.execute('UPDATE jupyter_talon SET last_login=?,\
                                          local_port=?,\
                                          talon_port=?,\
                                          login_node=?,\
                                          count_logins=?,\
                                          pid_session=?,\
                                          state_session=? WHERE euid=?', (
                last_login,
                local_port,
                talon_port,
                login_node,
                count_logins,
                pid_session,
                state_session,
                euid))
            logger(user=euid, message="USER %s STATE '%s' LOCAL_PORT %s HPC_PORT %s HOSTNAME %s" %
                   (euid, state_session, local_port, talon_port, login_node), level='INFO')
        else:
            # EUID NOT IN DB
            # ADD EUID IN DB
            first_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('INSERT INTO jupyter_talon VALUES (?,?,?,?,?,?,?,?,?)', (euid,
                                                                               first_login,
                                                                               last_login,
                                                                               local_port,
                                                                               talon_port,
                                                                               login_node,
                                                                               0,
                                                                               pid_session,
                                                                               state_session))
        # SAVE (COMMIT) THE CHANGES
        conn.commit()
        # CLOSE CONNECITON
        conn.close()
    except Exception as e:
        logger(user=euid, message='\tadd_db FAILED! %s' %
               str(e), level='ERROR')
    return


def from_db(db_name, euid):
    """Extract row from dabatase of a specific user.

    Args:
        db_name: Database name used to read.
        euid: User id of returned instance.
    Return:
        row: Row in database from euid.
    """

    row = None
    columns = ['first_login', 'last_login', 'local_port', 'talon_port',
               'login_node', 'count_logins', 'pid_session', 'state_session']
    try:
        # CHECK IF DB EXISTS OR NOT
        if os.path.isfile(db_name):
            # CONNECT TO DB
            conn = sqlite3.connect(db_name)
            # DB CONNECTION
            c = conn.cursor()
            # CHECK IF EUID EXISTS
            euids = list(
                c.execute('SELECT euid FROM jupyter_talon ORDER BY euid').fetchall())
            if (euid,) in euids:
                # EXTRACT ROW
                row = list(c.execute('SELECT first_login,\
                                    last_login,\
                                    local_port,\
                                    talon_port,\
                                    login_node,\
                                    count_logins,\
                                    pid_session,\
                                    state_session FROM jupyter_talon WHERE euid=?', (euid,)).fetchall())
                # DICTIONARY FORMAT
                row = {k: v for k, v in zip(columns, row[0])}
                logger(user=euid, message='USER %s RETRIEVED FROM DB!' %
                       euid, level='INFO')
            else:
                logger(user=euid, message='EUID %s NOT ADDED TO DB!' %
                       euid, level='WARNING')
        else:
            logger(user=euid, message='DB %s does not exist!' %
                   db_name, level='WARNING')
    except Exception as e:
        logger(user=euid, message='from_db FAILED! %s' % str(e), level='ERROR')
    return row


def jupyter_port(euid, passw, addrs, running_pid, timeout=5):
    """Jupyter configure and checking running instances.
    This function executes following procedures:
        USER EXISTS:
            - CHECK IF USER EXISTS
        CHECK IF jupyter_notebook_config.json EXISTS
            - JUPYTER CONFIG EXISTS:
        CHECK IF JUPYTER CONFIG EXISTS
        REQUEST HASH PASSWORD SHA1
            - GRAB SHA1 HASH:   CHECK IF HASH EXISTS
        REMOVE POTENTIAL jupyter_notebook_config.py FILE
        RECREATE jupyter_notebook_config.py FILE
            - CONFIGURE jupyter_notebook_config.py:
        ALLOW REMOTE ACCESS
        TIMEOUT KILL NOTEBOOK
        CHECK RUNNING NOTEBOOKS
            - LOOKING FOR RUNNING JUPYTER INSTANCES:
        CHECK IF RUNNING JUPYTER
            - GRAB LAST RUNNING JUPYTER NOTEBOOK PORT
            - CHECK IF JUPYTER CONFIG NOT EXISTS:
        JUPYTER CONFIG NOT EXISTS AND USER EXISTS
        JUPYTER CONFIG CREATED
            - CHECK IF FOUND NEWLY CREATED JUPYTER CONFIGURATION:
        FOUND NEWLY CREATED JUPYTER CONFIG
    Args:
        euid: User id.
        passw: Password for login to HPC.
        addrs: Hostname of HPC.
        running_pid: Current PID of process running.
        timeout: Seconds until end session.
    Return:
        is_user: True / Flase if user exists on HPC.
        is_jupyter_config: True / Flase if user has proper jupyter configure file.
        jupyter_sha: User specific password key.
        jupyter_last_port: Last running jupyter session port on HPC.
    """

    logger(user=euid, message='CHECK IF ANY RUNNING JUPYTER and HASH AND JUPYTER CONFIG', level='INFO')
    # UPDATE USER IN DATABASE
    add_db(db_name=DB_NAME,
           euid=euid,
           last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
           local_port=0,
           talon_port=0,
           login_node=LOGIN_NODE,
           pid_session=running_pid,
           state_session='initiated')

    child = pexpect.spawn('ssh %s@%s -o StrictHostKeyChecking=no' %
                          (euid, addrs), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)

    # SHELL COMMANDS
    shell_change_path = "cd /storage/scratch2/%s"%(euid)
    shell_ipy_dir = "export IPYTHONDIR=/storage/scratch2/%s/.ipython"%(euid)
    shell_jupyter_config_dir = "export JUPYTER_CONFIG_DIR=/storage/scratch2/%s/.jupyter"%(euid)
    shell_jupyter_data_dir = "export JUPYTER_DATA_DIR=/storage/scratch2/%s/.jupyter"%(euid)
    shell_jupyter_generate_config = "/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook --generate-config -y"

    shell_jupyter_config_path = "python -c \"import os; print('jupyter_config: ',os.path.exists('/storage/scratch2/%s/.jupyter/jupyter_notebook_config.json'))\""%(euid)
    shell_jupyter_config_sha = "awk -F\": \" '/\"password\": /{print $2;}' /storage/scratch2/%s/.jupyter/jupyter_notebook_config.json"%(euid)
    shell_jupyter_running = "/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook list"

    # STAUS VARIABLES
    jupyter_sha = None
    jupyter_last_port = None

    # STATE BOOLEAN VARIABLES
    is_jupyter_config = False
    is_user = False
    checking_running_jupyters = False
    configuring_jupyter = False

    # JUPYTER CONFIG FILE
    allow_remote_access = "sed -i 's/#c.NotebookApp.allow_remote_access = False/c.NotebookApp.allow_remote_access = True/g' .jupyter/jupyter_notebook_config.py"
    cull_busy = "sed -i 's/#c.MappingKernelManager.cull_busy = False/c.MappingKernelManager.cull_busy = False/g' .jupyter/jupyter_notebook_config.py"
    cull_connected = "sed -i 's/#c.MappingKernelManager.cull_connected = False/c.MappingKernelManager.cull_connected = False/g' .jupyter/jupyter_notebook_config.py"
    cull_idle_timeout = "sed -i 's/#c.MappingKernelManager.cull_idle_timeout = 0/c.MappingKernelManager.cull_idle_timeout = 10/g' .jupyter/jupyter_notebook_config.py"
    cull_interval = "sed -i 's/#c.MappingKernelManager.cull_interval = 300/c.MappingKernelManager.cull_interval = 5/g' .jupyter/jupyter_notebook_config.py"
    kernel_info_timeout = "sed -i 's/#c.MappingKernelManager.kernel_info_timeout = 60/c.MappingKernelManager.kernel_info_timeout = 60/g' .jupyter/jupyter_notebook_config.py"
    shutdown_no_activity_timeout = "sed -i 's/#c.NotebookApp.shutdown_no_activity_timeout = 0/c.NotebookApp.shutdown_no_activity_timeout = %s/g' .jupyter/jupyter_notebook_config.py"%JUPYTER_HPC_TIMEOUT

    # LOOP CHECK SHELL
    while True:
        try:
            child.expect('\n')
            out_line = child.before
            # ONLY LOG
            logger(user=euid, message=str(out_line),
                   level='INFO', verbose=False)
            # print("out_line", out_line)

            # CHECK IF USER EXISTS
            if "Last login:" in out_line:
                # USER EXISTS
                is_user = True
                logger(user=euid, message='\tUSER EXISTS', level='INFO')
                # CHANGE PATH
                child.sendline(shell_change_path)
                # ADD ENVIROMENT VARIABLES
                child.sendline(shell_ipy_dir)
                child.sendline(shell_jupyter_config_dir)
                child.sendline(shell_jupyter_data_dir)
                # JUPYTER GENERATE CONFIG
                child.sendline(shell_jupyter_generate_config)
                # CHECK IF jupyter_notebook_config.json EXISTS
                child.sendline(shell_jupyter_config_path)

            # CHECK IF JUPYTER CONFIG AND USER EXISTS
            if ("('jupyter_config: ', True)" in out_line) and is_user:
                # JUPYTER CONFIG EXISTS
                is_jupyter_config = True
                logger(user=euid, message='\tJUPYTER CONFIG EXISTS', level='INFO')
                # REQUEST HASH PASSWORD SHA1
                child.sendline(shell_jupyter_config_sha)

            # CHECK IF HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("sha1:" in out_line) and is_jupyter_config:
                # GRAB SHA1 HASH
                logger(user=euid, message='\tGRAB SHA1 HASH', level='INFO')
                jupyter_sha = str(out_line.replace('"', '')).strip()
                logger(user=euid, message='\tjupyter_sha', level='INFO')
                # START JUPYTER CONFIGURATION
                configuring_jupyter = True
                # REMOVE POTENTIAL jupyter_notebook_config.py FILE
                child.sendline('rm .jupyter/jupyter_notebook_config.py')
                # RECREATE jupyter_notebook_config.py FILE
                child.sendline(
                    '/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook --generate-config')
                logger(
                    user=euid, message='\t\tCREATED jupyter_notebook_config.py FILE', level='INFO')

            # CONFIGURE jupyter_notebook_config.py
            if "Writing default config to:" in out_line and configuring_jupyter:
                # ALLOW REMOTE ACCESS
                child.sendline(allow_remote_access)
                # TIMEOUT KILL NOTEBOOK
                child.sendline(cull_busy)
                child.sendline(cull_connected)
                child.sendline(cull_idle_timeout)
                child.sendline(cull_interval)
                child.sendline(kernel_info_timeout)
                child.sendline(shutdown_no_activity_timeout)
                configuring_jupyter = False
                logger(
                    user=euid, message='\t\tJUPYTER CONFIG FILE FINISHED CONFIGURE', level='INFO')
                # CHECK RUNNING NOTEBOOKS
                child.sendline(shell_jupyter_running)

            # CHECK IF RUNNING JUPYTER and HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("Currently running servers:" in out_line) and jupyter_sha and (not configuring_jupyter):
                # LOOKING FOR RUNNING JUPYTER INSTANCES
                checking_running_jupyters = True
                jupyter_last_port = "no_ports"
                logger(
                    user=euid, message='\tLOOKING FOR RUNNING JUPYTER INSTANCES', level='INFO')

            # GRAB LAST RUNNING JUPYTER IF RUNNING JUPYTER and HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("http://" in out_line) and checking_running_jupyters:
                # GRAB LAST RUNNING JUPYTER PORT
                logger(
                    user=euid, message='\tGRAB LAST RUNNING JUPYTER NOTEBOOK PORT', level='INFO')
                jupyter_last_port = out_line.split(":")[2].split("/")[0]
                # STOP LOOKING FOR RUNNING JUPYTER NOTEBOOKS SERVERS
                checking_running_jupyters = False
                logger(user=euid, message='\t\tjupyter_last_port %s' %
                       jupyter_last_port, level='INFO')
                child.close(force=True)
                return is_user, is_jupyter_config, jupyter_sha, jupyter_last_port

            # CHECK IF JUPYTER CONFIG NOT EXISTS AND USER EXISTS
            if ("('jupyter_config: ', False)" in out_line) and is_user:
                # JUPYTER CONFIG NOT EXISTS AND USER EXISTS
                logger(
                    user=euid, message='\tJUPYTER CONFIG NOT EXISTS AND USER EXISTS', level='INFO')
                # CREATE JUPYTER PASSWORD
                child.sendline(
                    "/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook password")
                child.expect("Enter password:")
                child.sendline(passw)
                child.expect("Verify password:")
                child.sendline(passw)
                logger(user=euid, message='\t\tJUPYTER CONFIG CREATED', level='INFO')

            # CHECK IF FOUND NEWLY CREATED JUPYTER CONFIGURATION
            if ("Wrote hashed password to" in out_line):
                logger(
                    user=euid, message='\tFOUND NEWLY CREATED JUPYTER CONFIG', level='INFO')
                child.sendline(shell_jupyter_config_path)

        except:
            logger(user=euid, message='\tjupyter_port ENDED!', level='WARNING')
            child.close(force=True)
            break

    if jupyter_last_port == "no_ports":
        logger(user=euid, message='\tNO RUNNING JUPYTER NOTEBOOK', level='WARNING')
    return is_user, is_jupyter_config, jupyter_sha, jupyter_last_port


def run_jupyter(euid, passw, addrs, timeout=10):
    """Start jupyter noteook on HPC in local VM background process.

    Args:
        euid: User id.
        passw: Password for login to HPC.
        addrs: Hostname of HPC.
        timeout: Seconds until end session.
    """
    shell_change_path = "cd /storage/scratch2/%s"%(euid)
    shell_ipy_dir = "export IPYTHONDIR=/storage/scratch2/%s/.ipython"%(euid)
    shell_jupyter_config_dir = "export JUPYTER_CONFIG_DIR=/storage/scratch2/%s/.jupyter"%(euid)
    shell_jupyter_data_dir = "export JUPYTER_DATA_DIR=/storage/scratch2/%s/.jupyter"%(euid)

    logger(user=euid, message='STARTING JUPYTER NOTEBOOK', level='INFO')
    child = pexpect.spawn("ssh %s@%s -o StrictHostKeyChecking=no \"cd %s && export %s && export %s && export %s && jupyter lab --no-browser --ip=0.0.0.0\" &"%
                        (euid,
                        addrs,
                        shell_change_path,
                        shell_ipy_dir,
                        shell_jupyter_config_dir,
                        shell_jupyter_data_dir), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)
    # LOOP CHECK SHELL
    while True:
        try:
            child.expect('\n')
            out_line = child.before
            logger(user=euid, message='STARTING JUPYTER NOTEBOOK: %s'%out_line, level='INFO', verbose=False)
            # print("out_line", out_line)
        except:
            logger(user=euid, message='\tRUNNING JUPYTER NOTEBOOK', level='INFO')
            child.close(force=True)
            break
    return


def forward_port(euid, passw, addrs, remote_port, local_port, running_pid, timeout=5):
    """Forward port of running instance from HPC to local VM.
    WITH A RUNNING JUPYTER INSTANCE ON A KNOWN PORT:
        - FORWARD KNOWN PORT TO GATEWAY
        - LOGIN IS SUCCESSFULL
        - LOGIN FAILED

    Args:
        euid: User id.
        passw: Password for login to HPC.
        addrs: Hostname of HPC.
        local_port: Port on local VM gateway used to forward.
        talon_port: Port on HPC needed to forward.
        running_pid: Pid of running process that does ssh tunneling.
        timeout: Seconds until end session.
    """

    logger(user=euid, message='FORWARD RUNNING JUPYTER INSTANCE PORT', level='INFO')
    child = pexpect.spawn('ssh -L 0.0.0.0:%s:127.0.0.1:%s  %s@%s -o StrictHostKeyChecking=no' %
                          (local_port, remote_port, euid, addrs), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)
    # login staus variables
    first_line = False
    is_logged = False
    # LOOP CHECK SHELL
    while True:
        try:
            child.expect('\n')
            out_line = child.before
            # print("out_line", out_line)

            # FIRST LINE OF THE LOGIN
            if (" " in out_line) and not first_line:
                first_line = True

            # LOGIN IS SUCCESSFULL
            if ("Last login:" in out_line) and first_line:
                is_logged = True
                logger(
                    user=euid, message='\tLOGIN IS SUCCESSFULL! FORWARDING...', level='CRITICAL')
                # UPDATE USER DATABASE
                add_db(db_name=DB_NAME,
                       euid=euid,
                       last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       local_port=local_port,
                       talon_port=remote_port,
                       login_node=LOGIN_NODE,
                       pid_session=running_pid,
                       state_session='running')

            # LOGIN FAILED
            if ("Last login:" not in out_line) and first_line and not is_logged:
                logger(user=euid, message='\tLOGIN FAILED!', level='ERROR')
                # UPDATE USER DATABASE
                add_db(db_name=DB_NAME,
                       euid=euid,
                       last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       local_port=local_port,
                       talon_port=remote_port,
                       login_node=LOGIN_NODE,
                       pid_session=running_pid,
                       state_session='ended')
                child.close(force=True)
                break

        except:
            logger(user=euid, message='\tforward_port ENDED', level='WARNING')
            # UPDATE USER INFO
            add_db(db_name=DB_NAME,
                   euid=euid,
                   last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   local_port=local_port,
                   talon_port=remote_port,
                   login_node=LOGIN_NODE,
                   pid_session=running_pid,
                   state_session='ended')
            child.close(force=True)
            break
    return


def jupyter_instance(conn, _euid, _pass, hostname, session_timeout):
    """Functions wrapper to check if user exists on HPC and forward
        any running jupyter instance port.

    Args:
        conn: Multi-process connection.
        _euid: User id.
        _pass: Password for login to HPC.
        hostname: Hostname of HPC.
        session_timeout: Seconds until end session.
    """

    pid_session = os.getpid()
    random_local_port = find_free_port()
    is_user, is_jupyter_config, jupyter_sha, jupyter_last_port = jupyter_port(
        euid=_euid, passw=_pass, addrs=hostname, running_pid=pid_session, timeout=5)

    if is_user and is_jupyter_config and jupyter_last_port == "no_ports":
        logger(
            user=_euid, message='NO PORTS FOUND! START JUPYTER INSTANCE', level='WARNING')
        run_jupyter(euid=_euid, passw=_pass, addrs=hostname, timeout=5)
        _, _, _, jupyter_last_port = jupyter_port(
            euid=_euid, passw=_pass, running_pid=pid_session, addrs=hostname, timeout=5)

        if jupyter_last_port and (jupyter_last_port != "no_ports"):
            logger(user=_euid, message='FORWARD PORT', level='INFO')
            # send message
            send_line = "running %s %s %s" % (
                jupyter_last_port, random_local_port, pid_session)
            conn.send(send_line)
            conn.close()
            forward_port(euid=_euid, passw=_pass, addrs=hostname, remote_port=jupyter_last_port,
                         local_port=random_local_port, timeout=session_timeout, running_pid=pid_session)

    elif jupyter_last_port and (jupyter_last_port != "no_ports"):
        logger(user=_euid, message='FORWARD PORT', level='INFO')
        # send message
        send_line = "running %s %s %s" % (
            jupyter_last_port, random_local_port, pid_session)
        conn.send(send_line)
        conn.close()
        forward_port(euid=_euid, passw=_pass, addrs=hostname, remote_port=jupyter_last_port,
                     local_port=random_local_port, timeout=session_timeout, running_pid=pid_session)

    else:
        logger(user=_euid, message='COMPLETE FAIL!', level='ERROR')
        # send message
        send_line = "ended %s %s %s" % (jupyter_last_port, random_local_port, pid_session)
        conn.send(send_line)
        conn.close()
    return


# create the Flask application object
app = Flask(__name__)

# use decorators to link the function to a url
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
        use = request.form['username']
        pas = request.form['password']

        logger(user='root', message='Request method: %s euid: %s ip: %s'%(request_method, use, request_ip), level='WARNING')
        # CHECK IF EUID ALREADY INITIATED
        euid_log = from_db(db_name=DB_NAME, euid=use)

        # USER NEVER LOGGED IN
        if euid_log is None:
            # UPDATE USER IN DATABASE
            add_db(db_name=DB_NAME,
                   euid=use,
                   last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   local_port=0,
                   talon_port=0,
                   login_node=LOGIN_NODE,
                   pid_session=0,
                   state_session='initiated')

            # creating a sesion pipe communication
            parent_conn, child_conn = Pipe()
            # start session - updates database
            p = Process(target=jupyter_instance, args=(
                parent_conn, use, pas, LOGIN_NODE, SESSION_TIME))
            p.start()

            # expect communication from instance pipe communicaiton
            receive_line = child_conn.recv()
            # only retrieves 'running' and 'ended'
            state_session, jupyter_last_port, random_local_port, pid_session = receive_line.split()

            # check state of instance
            if state_session == 'ended':
                # connection failed - update database
                add_db(db_name=DB_NAME,
                       euid=use,
                       last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       local_port=jupyter_last_port,
                       talon_port=jupyter_last_port,
                       login_node=LOGIN_NODE,
                       pid_session=pid_session,
                       state_session=state_session)
                error = 'Invalid Credentials. Please try again.'
                logger(user=use, message=error, level='ERROR')
                return render_template('login.html', error=error)
            else:
                # connection is successfull - forward to jupyter
                ide_link = "http://hpc-gateway.hpc.unt.edu:%s" % (
                    random_local_port)
                # update user database
                add_db(db_name=DB_NAME,
                       euid=use,
                       last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       local_port=jupyter_last_port,
                       talon_port=jupyter_last_port,
                       login_node=LOGIN_NODE,
                       pid_session=pid_session,
                       state_session=state_session)
                time.sleep(5)
                logger(
                    user=use, message='connection is successfull - forward to jupyter', level='INFO')
                return redirect(ide_link)

        # USER IN PROCESS OF LOGGING IN
        elif euid_log['state_session'] == 'initiated':
            print('LOGIN ALREADY INITIATED!')
            # connection failed
            error = 'Login Already Initiated!'
            logger(user=use, message=error, level='WARNING')
            return render_template('login.html', error=error)

        elif (euid_log['state_session'] == 'running') or (euid_log['state_session'] == 'ended'):
            # RUN JUPYTER SEQUENCE:
            # KILL PREVIOUS PID
            kill_pid(pid=euid_log['pid_session'])
            # UPDATE USER IN DATABASE
            add_db(db_name=DB_NAME,
                   euid=use,
                   last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   local_port=0,
                   talon_port=0,
                   login_node=LOGIN_NODE,
                   pid_session=0,
                   state_session='initiated')

            # creating a sesion pipe communication
            parent_conn, child_conn = Pipe()

            # start session
            p = Process(target=jupyter_instance, args=(
                parent_conn, use, pas, LOGIN_NODE, SESSION_TIME))
            p.start()

            # expect communication from instance pipe communicaiton
            receive_line = child_conn.recv()
            state_session, jupyter_last_port, random_local_port, pid_session = receive_line.split()

            # UPDATE USER IN DATABASE
            add_db(db_name=DB_NAME,
                   euid=use,
                   last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   local_port=jupyter_last_port,
                   talon_port=jupyter_last_port,
                   login_node=LOGIN_NODE,
                   pid_session=pid_session,
                   state_session=state_session)

            # check state of instance
            if state_session == 'ended':
                # connection failed
                error = 'Invalid Credentials. Please try again.'
                logger(user=use, message=error, level='ERROR')
                return render_template('login.html', error=error)
            else:
                # connection is successfull - forward to jupyter
                ide_link = "http://hpc-gateway.hpc.unt.edu:%s" % (
                    random_local_port)
                # return render_template('login.html', ide_link=ide_link, ide_password="Your Talon Password")
                time.sleep(5)
                logger(
                    user=use, message='connection is successfull - forward to jupyter', level='INFO')
                return redirect(ide_link)
    else:
        # request method is 'GET'
        logger(user='root', message='Request method: %s ip: %s'%(request_method, request_ip), level='WARNING')

    return render_template('login.html', login='login')


if __name__ == '__main__':
    # CHECK LOGS FOLDER
    # CHECK DB
    if create_db(db_name=DB_NAME):
        print(' * Databased checked!')
        app.run(host='0.0.0.0', debug=True, threaded=True)
    else:
        print('Database failed!')
