# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""Extra functions file.
    logger


(C) 2020 George Mihaila
email georgemihaila@my.unt.edu
"""
import sys
from io import StringIO
import os
import time
from datetime import datetime
import socket
from contextlib import closing


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
