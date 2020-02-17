# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""Python Flask Server to automate Jupyter Lab port forward on HPC cluster.
Start the server with the 'run()' method

(C) 2020 George Mihaila
email georgemihaila@my.unt.edu
"""
import sys
from io import StringIO
import os
import time
from datetime import datetime
import sqlite3
import socket
from contextlib import closing
from helper_functions import logger


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
                  (user, first_login, last_login, local_port, talon_port, login_node, count_logins, pid_session , state_session)''')
            # SAVE (COMMIT) THE CHANGES
            conn.commit()
            # CLOSE CONNECITON
            conn.close()

        return True
    except Exception as e:
        logger(user='root', message='DB FAILED! %s' % str(e), level='ERROR')
        return False


def add_db(db_name, user, last_login, local_port, talon_port, login_node, pid_session, state_session):
    '''Add instance in database or create database if it does not exist.
    Columns: 'user', 'first_login', 'last_login', 'local_port', 'talon_port',
        'login_node', 'count_logins', 'pid_session', 'state_session'.

    Args:
        db_name: Database name.
        user: User id.
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
                  (user, first_login, last_login, local_port, talon_port, login_node, count_logins, pid_session , state_session)''')
        else:
            # DB EXISTS - JUST ESTABLISH CONNECTION
            # CONNECT TO DB
            conn = sqlite3.connect(db_name)
            # DB CONNECTION
            c = conn.cursor()

        # CHECK IF USER ALREADY EXISTS
        users = list(
            c.execute('SELECT user FROM jupyter_talon ORDER BY user').fetchall())
        if (user,) in users:
            # user ALREADY IN DB
            # GRAB NUMBER OF LOGINS
            count_logins = (c.execute(
                'SELECT count_logins FROM jupyter_talon WHERE user=?', (user,)).fetchall())[0][0]
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
                                          state_session=? WHERE user=?', (
                last_login,
                local_port,
                talon_port,
                login_node,
                count_logins,
                pid_session,
                state_session,
                user))
            logger(user=user, message="USER %s STATE '%s' LOCAL_PORT %s HPC_PORT %s HOSTNAME %s" %
                   (user, state_session, local_port, talon_port, login_node), level='INFO')
        else:
            # user NOT IN DB
            # ADD user IN DB
            first_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('INSERT INTO jupyter_talon VALUES (?,?,?,?,?,?,?,?,?)', (user,
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
        logger(user=user, message='\tadd_db FAILED! %s' %
               str(e), level='ERROR')
    return


def from_db(db_name, user):
    """Extract row from dabatase of a specific user.

    Args:
        db_name: Database name used to read.
        user: User id of returned instance.
    Return:
        row: Row in database from user.
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
            # CHECK IF user EXISTS
            users = list(
                c.execute('SELECT user FROM jupyter_talon ORDER BY user').fetchall())
            if (user,) in users:
                # EXTRACT ROW
                row = list(c.execute('SELECT first_login,\
                                    last_login,\
                                    local_port,\
                                    talon_port,\
                                    login_node,\
                                    count_logins,\
                                    pid_session,\
                                    state_session FROM jupyter_talon WHERE user=?', (user,)).fetchall())
                # DICTIONARY FORMAT
                row = {k: v for k, v in zip(columns, row[0])}
                logger(user=user, message='USER %s RETRIEVED FROM DB!' %
                       user, level='INFO')
            else:
                logger(user=user, message='user %s ADDED TO DB!' %
                       user, level='WARNING')
        else:
            logger(user=user, message='DB %s does not exist!' %
                   db_name, level='WARNING')
    except Exception as e:
        logger(user=user, message='from_db FAILED! %s' % str(e), level='ERROR')
    return row
