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


def forward_jupyter(euid, passw, addrs, remote_port, local_port, running_pid, timeout=10):
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

    # SHELL COMMANDS
    shell_change_path = "cd /storage/scratch2/%s"%(euid)
    shell_ipy_dir = "export IPYTHONDIR=/storage/scratch2/%s/.ipython"%(euid)
    shell_jupyter_config_dir = "export JUPYTER_CONFIG_DIR=/storage/scratch2/%s/.jupyter"%(euid)
    shell_jupyter_data_dir = "export JUPYTER_DATA_DIR=/storage/scratch2/%s/.jupyter"%(euid)
    shell_module_load = "module load anaconda"

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
            print("out_line", out_line)

            # FIRST LINE OF THE LOGIN
            if (" " in out_line) and not first_line:
                first_line = True

            # LOGIN IS SUCCESSFULL
            if ("Last login:" in out_line) and first_line:
                is_logged = True
                logger(
                    user=euid, message='\tLOGIN IS SUCCESSFULL! FORWARDING...', level='CRITICAL')
                # CHANGE PATH
                child.sendline(shell_change_path)
                # # ADD ENVIROMENT VARIABLES
                child.sendline('export PATH="$PATH:/cm/shared/utils/PYTHON/3.6.5/bin"')
                child.sendline('export PATH="$PATH:/cm/shared/utils/PYTHON/3.6.5/lib"')
                child.sendline('export PATH="$PATH:/cm/shared/utils/PYTHON/ANACONDA/5.2/bin"')
                child.sendline('export PATH="$PATH:/cm/shared/utils/PYTHON/ANACONDA/5.2/lib"')
                child.sendline(shell_ipy_dir)
                child.sendline(shell_jupyter_config_dir)
                child.sendline(shell_jupyter_data_dir)
                child.sendline('jupyter lab --no-browser --ip=0.0.0.0 --port=%s'%remote_port)
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

if __name__ == '__main__':
    forward_jupyter(euid='gm0234', passw='', addrs=LOGIN_NODE, remote_port='39634', local_port='39634', running_pid='0', timeout=10)
