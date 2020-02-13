# !/usr/bin/env python
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

PYTHON_PATH = '/cm/shared/utils/PYTHON/3.6.5'
CONDA_PATH = '/cm/shared/utils/PYTHON/ANACONDA/5.2'

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


def jupyter_forward(euid, passw, addrs, remote_port, local_port, running_pid, timeout=10):
    """Forward port of running instance from HPC to local VM.
    Start new Jupyter instance if nothing running.
    WITH A RUNNING JUPYTER INSTANCE ON A KNOWN PORT:
        - FORWARD KNOWN PORT TO GATEWAY
        - LOGIN IS SUCCESSFULL
        - LOGIN FAILED
    Update users state to 'initialized' before running this function.

    Args:
        euid: User id.
        passw: Password for login to HPC.
        addrs: Hostname of HPC.
        remote_port: Port used on HPC.
        local_port: Port on local VM gateway used to forward.
        running_pid: Pid of running process that does ssh tunneling.
        timeout: Seconds until end session.
    """

    # GRAB CURRENT REMOTE PORT FROM DB
    current_remote_port = None
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
            logger(user=euid, message=str(out_line), level='INFO')
            # print("out_line", out_line)

            # FIRST LINE OF THE LOGIN
            if (" " in out_line) and not first_line:
                first_line = True

            # LOGIN IS SUCCESSFULL
            if ("Last login:" in out_line) and first_line:
                is_logged = True
                logger(user=euid, message='LOGIN IS TO HPC SUCCESSFULL! START JUPYTER...', level='CRITICAL')
                # CHANGE PATH
                child.sendline("cd /storage/scratch2/%s"%euid)
                # ADD ENVIROMENT VARIABLES
                child.sendline('export PATH="$PATH:%s/bin"'%CONDA_PATH)
                child.sendline('export PATH="$PATH:%s/lib"'%CONDA_PATH)
                child.sendline('export PATH="$PATH:%s/bin"'%PYTHON_PATH)
                child.sendline('export PATH="$PATH:%s/lib"'%PYTHON_PATH)
                child.sendline("export IPYTHONDIR=/storage/scratch2/%s/.ipython"%euid)
                child.sendline("export JUPYTER_CONFIG_DIR=/storage/scratch2/%s/.jupyter"%euid)
                child.sendline("export JUPYTER_DATA_DIR=/storage/scratch2/%s/.jupyter"%euid)
                if remote_port!=current_remote_port:
                    # NEED NEW JUPYTER INSTANCE
                    child.sendline('jupyter lab --no-browser --ip=0.0.0.0 --port=%s'%remote_port)
            # JUPYTER STARTED SUCCESSFULLY
            if ('The Jupyter Notebook is running at' in out_line) and is_logged and remote_port:
                logger(user=euid, message='JUPYTER STARTED SUCCESSFULLY. LOCAL PORT: %s REMOTE PORT: %s'%
                        (local_port, remote_port), level='CRITICAL')
                # UPDATE USER DATABASE
                # add_db(db_name=DB_NAME,
                #        euid=euid,
                #        last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                #        local_port=local_port,
                #        talon_port=remote_port,
                #        login_node=LOGIN_NODE,
                #        pid_session=running_pid,
                #        state_session='running')

            # LOGIN FAILED
            if ("Last login:" not in out_line) and first_line and not is_logged:
                logger(user=euid, message='\tLOGIN FAILED!', level='ERROR')
                # UPDATE USER DATABASE
                # add_db(db_name=DB_NAME,
                #        euid=euid,
                #        last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                #        local_port=local_port,
                #        talon_port=remote_port,
                #        login_node=LOGIN_NODE,
                #        pid_session=running_pid,
                #        state_session='ended')
                child.close(force=True)
                break

        except:
            logger(user=euid, message='\tforward_port ENDED', level='WARNING')
            # UPDATE USER INFO
            # add_db(db_name=DB_NAME,
            #        euid=euid,
            #        last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            #        local_port=local_port,
            #        talon_port=remote_port,
            #        login_node=LOGIN_NODE,
            #        pid_session=running_pid,
            #        state_session='ended')
            child.close(force=True)
            break
    return


def jupyter_configure(euid, passw, addrs, running_pid, timeout=5):
    """Jupyter configure and checking running instances.
    if jupyter_last_port is same as remote_port from DB keep it.
    if jupyter_last_port is same as remote_port from DB keep but other user is using, change it.
    if jupyter_last_port is None in DB, create new one.
    This function executes following procedures:
        - Check if user exists.
        Change path to scratch2.
        Export enviroment variables (python and conda paths).
        Run jupyter config command.

    Args:
        euid: User id.
        passw: Password for login to HPC.
        addrs: Hostname of HPC.
        timeout: Seconds until end session.
    Return:
        is_user: True / Flase if user exists on HPC.
        is_jupyter_config: True / Flase if user has proper jupyter configure file.
        jupyter_last_port: Last running jupyter session port on HPC.
    """

    # GET REMOTE PORT FROM USER DB [IF OTHER USER IS USING IT RETURN None]
    # IF NEVER HAD A PORT MAKE IT None
    remote_port = None

    logger(user=euid, message='CHECK IF ANY RUNNING JUPYTER and HASH AND JUPYTER CONFIG', level='INFO')
    # UPDATE USER IN DATABASE
    # add_db(db_name=DB_NAME,
    #        euid=euid,
    #        last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #        local_port=0,
    #        talon_port=0,
    #        login_node=LOGIN_NODE,
    #        pid_session=running_pid,
    #        state_session='initiated')

    child = pexpect.spawn('ssh %s@%s -o StrictHostKeyChecking=no' %
                          (euid, addrs), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)


    shell_jupyter_config_path = "python -c \"import os; print('jupyter_config: ',os.path.exists('/storage/scratch2/%s/.jupyter/jupyter_notebook_config.json'))\""%(euid)
    shell_jupyter_config_sha = "awk -F\": \" '/\"password\": /{print $2;}' /storage/scratch2/%s/.jupyter/jupyter_notebook_config.json"%(euid)
    shell_check_port = "python -c 'import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); print(\"port_used\",s.connect_ex((\"localhost\", %s)) == 0)'"%(remote_port)
    shell_new_port = ""
    # STAUS VARIABLES
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
    notebook_dir = "sed -i \"s/#c.NotebookApp.notebook_dir = ''/c.NotebookApp.notebook_dir = '\\/storage\\/scratch2\\/%s\\/.jupyter'/g\" .jupyter/jupyter_notebook_config.py"%(euid)
    map_root_dir = "sed -i \"s/#c.MappingKernelManager.root_dir = ''/c.MappingKernelManager.root_dir = '\\/storage\\/scratch2\\/%s\\/.ipython'/g\" .jupyter/jupyter_notebook_config.py"%(euid)
    content_root_dir = "sed -i \"s/#c.ContentsManager.root_dir = '\\/'/c.ContentsManager.root_dir = '\\/storage\\/scratch2\\/%s'/g\" .jupyter/jupyter_notebook_config.py"%(euid)
    iopub_data_rate_limit = "sed -i 's/#c.NotebookApp.iopub_data_rate_limit = 1000000/c.NotebookApp.iopub_data_rate_limit = 1e10/g' .jupyter/jupyter_notebook_config.py"
    mathjax_config = "sed -i \"s/#c.NotebookApp.mathjax_config = 'TeX-AMS-MML_HTMLorMML-full,Safe'/c.NotebookApp.mathjax_config = 'TeX-AMS-MML_HTMLorMML-full,Safe'/g\" .jupyter/jupyter_notebook_config.py"


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
                logger(user=euid, message='USER EXISTS!', level='INFO')
                # CHANGE PATH
                child.sendline("cd /storage/scratch2/%s"%euid)
                # ADD ENVIROMENT VARIABLES
                child.sendline('export PATH="$PATH:%s/bin"'%PYTHON_PATH)
                child.sendline('export PATH="$PATH:%s/lib"'%PYTHON_PATH)
                child.sendline('export PATH="$PATH:%s/bin"'%CONDA_PATH)
                child.sendline('export PATH="$PATH:%s/lib"'%CONDA_PATH)
                child.sendline("export IPYTHONDIR=/storage/scratch2/%s/.ipython"%euid)
                child.sendline("export JUPYTER_CONFIG_DIR=/storage/scratch2/%s/.jupyter"%euid)
                child.sendline("export JUPYTER_DATA_DIR=/storage/scratch2/%s/.jupyter"%euid)
                # REMOVE POTENTIAL jupyter_notebook_config.py FILE
                # child.sendline('rm  .jupyter')
                # JUPYTER GENERATE CONFIG .jupyter
                child.sendline("jupyter notebook --generate-config -y")
                # CREATE .ipyton if not created
                child.sendline('mkdir -p .ipython')
                logger(user=euid, message='TRY TO CREATE jupyter_notebook_config.py', level='INFO')
                # CHECK IF jupyter_notebook_config.json CREATED with
                child.sendline(shell_jupyter_config_path)

            # CHECK IF JUPYTER CONFIG EXISTS. KNOW THAT USER EXISTS
            if ('Writing default config to:' in out_line) and is_user:
                # SET PASSWORD
                # CHANGE jupyter_notebook_config.py
                is_jupyter_config = True
                logger(user=euid, message='CREATED jupyter_notebook_config.py!', level='CRITICAL')
                # CREATE JUPYTER PASSWORD
                child.sendline("jupyter notebook password")
                child.expect("Enter password:")
                child.sendline(passw)
                child.expect("Verify password:")
                child.sendline(passw)

            # CHANGE jupyter_notebook_config.py. KNOW THAT JUPYTER PASSWORD IS SET.
            if ('Wrote hashed password to' in out_line) and is_jupyter_config:
                logger(user=euid, message='JUPYTER PASSWORD IS SET!', level='CRITICAL')
                # ALLOW REMOTE ACCESS
                child.sendline(allow_remote_access)
                # CONFIG FILE jupyter_config.py
                child.sendline(cull_busy)
                child.sendline(cull_connected)
                child.sendline(cull_idle_timeout)
                child.sendline(cull_interval)
                child.sendline(kernel_info_timeout)
                child.sendline(shutdown_no_activity_timeout)
                child.sendline(notebook_dir)
                child.sendline(map_root_dir)
                child.sendline(content_root_dir)
                child.sendline(iopub_data_rate_limit)
                child.sendline(mathjax_config)
                logger(user=euid, message='CONFIGURED jupyter_notebook_config.py!', level='CRITICAL')
                # GRAB LAST PORT OF RUNNING NOTEBOOK IF EXISTS


            # CHECK IF JUPYTER CONFIG NOT EXISTS. KNOW THAT USER EXISTS.
            if ("('jupyter_config: ', False)" in out_line) and is_user:
                # JUPYTER CONFIG NOT EXISTS AND USER EXISTS
                logger(user=euid, message='JUPYTER FAILED TO CREATE CONFIG FILE!',level='ERROR')
                logger(user=euid, message='FUNCTION ENDED!', level='ERROR')
                child.close(force=True)
                break


        except:
            logger(user=euid, message='FUNCTION ENDED!', level='WARNING')
            child.close(force=True)
            break

    if jupyter_last_port == "no_ports":
        logger(user=euid, message='NO RUNNING JUPYTER NOTEBOOK', level='WARNING')
    return is_user, is_jupyter_config, jupyter_last_port



if __name__ == '__main__':
    is_user, is_jupyter_config, jupyter_last_port = jupyter_configure(euid='gm0234', passw='', addrs=LOGIN_NODE, running_pid=2, timeout=5)
    print(is_user, is_jupyter_config, jupyter_last_port)
    # forward_new_jupyter(euid='gm0234', passw='', addrs=LOGIN_NODE, remote_port='39634', local_port='39634', running_pid='0', timeout=10)
