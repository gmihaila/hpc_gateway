#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Python Flask Server to automate Jupyter Lab port forward on HPC cluster.
Start the server with the 'run()' method

(C) 2020 George Mihaila
email georgemihaila@my.unt.edu
"""

import os
from datetime import datetime
import pexpect

from jupyter_lab import app, DATABASE_NAME, START_OPEN_PORT, END_OPEN_PORT
from helper_functions import logger, find_free_port
from sqlite_database import add_db



class JupyterLab(object):
    """
    Args:
        user: User id.
        passw: Password for login to HPC.
        addrs: Hostname of HPC.
        timeout: Seconds until end session.
    Return:
        is_user: True / Flase if user exists on HPC.
        running_jupyter: True / Flase if running jupyter instance or not.
        jupyter_port: Jupyter port, either last running instance or free port.
    """

    def __init__(self, user, credential, hostname, conda_pah, python_path, jupyter_bin_path, pid, session_length):
        self.user = user
        self.credential = credential
        self.hostname = hostname
        self.conda_pah = conda_pah
        self.python_path = python_path
        self.jupyter_bin_path = jupyter_bin_path
        self.pid = pid
        self.session_length = session_length
        self.timeout = 5
        return

    def configure(self,):
        """Jupyter configure and checking running instances.
        This function executes following procedures:
            - Check if user exists.
            Change path to scratch2.
            Export enviroment variables (python and conda paths).
            Run jupyter config command.
        """

        logger(user=self.user, message='CHECK IF ANY RUNNING JUPYTER and HASH AND JUPYTER CONFIG', level='INFO')
        # UPDATE USER IN DATABASE
        add_db(db_name=DATABASE_NAME,
               user=self.user,
               last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
               local_port=0,
               talon_port=0,
               login_node=self.hostname,
               pid_session=self.pid,
               state_session='initiated')

        child = pexpect.spawn('ssh %s@%s -o StrictHostKeyChecking=no' %
                              (self.user, self.hostname), encoding='utf-8', timeout=self.timeout, logfile=None)
        child.expect(['password: '])
        child.sendline(self.credential)


        shell_jupyter_config_path = "python -c \"import os; print('jupyter_config: ',os.path.exists('/storage/scratch2/%s/.jupyter/jupyter_notebook_config.json'))\""%(self.user)
        shell_free_port = "python -c 'import socket; s=socket.socket(); s.bind((\"\", 0)); print(\"free port:\",s.getsockname()[1])'"
        # STAUS VARIABLES
        jupyter_port = None

        # STATE BOOLEAN VARIABLES
        is_jupyter_config = False
        is_user = False
        checking_running_jupyter = False
        running_jupyter = False
        configuring_jupyter = False

        # JUPYTER CONFIG FILE
        allow_remote_access = "sed -i 's/#c.NotebookApp.allow_remote_access = False/c.NotebookApp.allow_remote_access = True/g' .jupyter/jupyter_notebook_config.py"
        cull_busy = "sed -i 's/#c.MappingKernelManager.cull_busy = False/c.MappingKernelManager.cull_busy = False/g' .jupyter/jupyter_notebook_config.py"
        cull_connected = "sed -i 's/#c.MappingKernelManager.cull_connected = False/c.MappingKernelManager.cull_connected = True/g' .jupyter/jupyter_notebook_config.py"
        cull_idle_timeout = "sed -i 's/#c.MappingKernelManager.cull_idle_timeout = 0/c.MappingKernelManager.cull_idle_timeout = %s/g' .jupyter/jupyter_notebook_config.py"%self.session_length
        cull_interval = "sed -i 's/#c.MappingKernelManager.cull_interval = 300/c.MappingKernelManager.cull_interval = 5/g' .jupyter/jupyter_notebook_config.py"
        kernel_info_timeout = "sed -i 's/#c.MappingKernelManager.kernel_info_timeout = 60/c.MappingKernelManager.kernel_info_timeout = 60/g' .jupyter/jupyter_notebook_config.py"
        shutdown_no_activity_timeout = "sed -i 's/#c.NotebookApp.shutdown_no_activity_timeout = 0/c.NotebookApp.shutdown_no_activity_timeout = %s/g' .jupyter/jupyter_notebook_config.py"%self.session_length
        notebook_dir = "sed -i \"s/#c.NotebookApp.notebook_dir = ''/c.NotebookApp.notebook_dir = '\\/storage\\/scratch2\\/%s\\/'/g\" .jupyter/jupyter_notebook_config.py"%(self.user)
        map_root_dir = "sed -i \"s/#c.MappingKernelManager.root_dir = ''/c.MappingKernelManager.root_dir = '\\/storage\\/scratch2\\/%s\\/.ipython'/g\" .jupyter/jupyter_notebook_config.py"%(self.user)
        content_root_dir = "sed -i \"s/#c.ContentsManager.root_dir = '\\/'/c.ContentsManager.root_dir = '\\/storage\\/scratch2\\/%s'/g\" .jupyter/jupyter_notebook_config.py"%(self.user)
        iopub_data_rate_limit = "sed -i 's/#c.NotebookApp.iopub_data_rate_limit = 1000000/c.NotebookApp.iopub_data_rate_limit = 1e10/g' .jupyter/jupyter_notebook_config.py"
        mathjax_config = "sed -i \"s/#c.NotebookApp.mathjax_config = 'TeX-AMS-MML_HTMLorMML-full,Safe'/c.NotebookApp.mathjax_config = 'TeX-AMS-MML_HTMLorMML-full,Safe'/g\" .jupyter/jupyter_notebook_config.py"

        # LOOP CHECK SHELL
        while True:
            try:
                child.expect('\n')
                out_line = child.before
                # ONLY LOG
                logger(user=self.user, message=str(out_line),
                       level='INFO', verbose=False)

                # CHECK IF USER EXISTS
                if "Last login:" in out_line:
                    # USER EXISTS
                    is_user = True
                    logger(user=self.user, message='USER EXISTS!', level='INFO')
                    # CHANGE PATH
                    child.sendline("cd /storage/scratch2/%s"%(self.user))
                    # ADD ENVIROMENT VARIABLES
                    child.sendline('export PATH="$PATH:%s/bin"'%(self.conda_pah))
                    child.sendline('export PATH="$PATH:%s/lib"'%(self.conda_pah))
                    child.sendline('export PATH="$PATH:%s/bin"'%(self.python_path))
                    child.sendline('export PATH="$PATH:%s/lib"'%(self.python_path))
                    child.sendline("export IPYTHONDIR=/storage/scratch2/%s/.ipython"%(self.user))
                    child.sendline("export JUPYTER_CONFIG_DIR=/storage/scratch2/%s/.jupyter"%(self.user))
                    child.sendline("export JUPYTER_DATA_DIR=/storage/scratch2/%s/.jupyter"%(self.user))
                    # REMOVE POTENTIAL jupyter_notebook_config.py FILE
                    # child.sendline('rm  .jupyter')
                    # JUPYTER GENERATE CONFIG .jupyter
                    child.sendline("%s notebook --generate-config -y"%(self.jupyter_bin_path))
                    # CREATE .ipyton if not created
                    child.sendline('mkdir -p .ipython')
                    # CREATE SYMBOLIK LINK TO HOME DIRECTORY IF NOT EXISTING
                    child.sendline('test ! -d /storage/scratch2/%s_home_dir && ln -s /home/%s/ %s_home_dir'%(self.user, self.user, self.user))
                    logger(user=self.user, message='TRY TO CREATE jupyter_notebook_config.py', level='INFO')
                    # CHECK IF jupyter_notebook_config.json CREATED with
                    child.sendline(shell_jupyter_config_path)

                # CHECK IF JUPYTER CONFIG EXISTS. KNOW THAT USER EXISTS
                if ('Writing default config to:' in out_line) and is_user:
                    # SET PASSWORD
                    # CHANGE jupyter_notebook_config.py
                    is_jupyter_config = True
                    logger(user=self.user, message='CREATED jupyter_notebook_config.py!', level='CRITICAL')
                    # CREATE JUPYTER PASSWORD
                    child.sendline("%s notebook password"%(self.jupyter_bin_path))
                    child.expect("Enter password:")
                    child.sendline(self.credential)
                    child.expect("Verify password:")
                    child.sendline(self.credential)

                # CHANGE jupyter_notebook_config.py. KNOW THAT JUPYTER PASSWORD IS SET.
                if ('Wrote hashed password to' in out_line) and is_jupyter_config:
                    logger(user=self.user, message='JUPYTER PASSWORD IS SET!', level='CRITICAL')
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
                    logger(user=self.user, message='CONFIGURED jupyter_notebook_config.py!', level='CRITICAL')
                    # GRAB UNUSED PORT ON HPC
                    child.sendline(shell_free_port)

                # GRAB FREE PORT [IN CASE OF NO RUNNING JUPYTER]
                if ("('free port:'," in out_line):
                    jupyter_port = (out_line.split(",")[1].split(")")[0])
                    logger(user=self.user, message='FOUND FREE PORT: %s'%jupyter_port,level='CRITICAL')
                    # GRAB LAST PORT OF RUNNING NOTEBOOK IF EXISTS
                    child.sendline('%s notebook list'%(self.jupyter_bin_path))

                # SEE RUNNING JUPYTER PORTS
                if ('Currently running servers:' in out_line):
                    # LOOKING FOR RUNNING JUPYTER INSTANCES
                    logger(user=self.user, message='LOOKING FOR RUNNING SERVERS',level='CRITICAL')
                    checking_running_jupyter = True

                # GRAB LAST RUNNING JUPYTER. KNOW THAT USERS EXISTS, COFIGURE SET AND LOOKING FOR JUPYTER
                if ("http://" in out_line) and checking_running_jupyter:
                    # GRAB LAST RUNNING JUPYTER PORT
                    logger(user=self.user, message='GRAB LAST RUNNING JUPYTER NOTEBOOK PORT', level='INFO')
                    jupyter_port = (out_line.split(":")[2].split("/")[0])
                    # FOUND RUNNING JUPYTER
                    running_jupyter = True
                    # STOP LOOKING FOR RUNNING JUPYTER NOTEBOOKS SERVERS
                    checking_running_jupyter = False
                    logger(user=self.user, message='jupyter_port %s' %
                           jupyter_port, level='CRITICAL')
                    child.close(force=True)
                    return is_user, running_jupyter, jupyter_port

                # CHECK IF JUPYTER CONFIG NOT EXISTS. KNOW THAT USER EXISTS.
                if ("('jupyter_config: ', False)" in out_line) and is_user:
                    # JUPYTER CONFIG NOT EXISTS AND USER EXISTS
                    logger(user=self.user, message='JUPYTER FAILED TO CREATE CONFIG FILE!',level='ERROR')
                    logger(user=self.user, message='FUNCTION ENDED!', level='ERROR')
                    child.close(force=True)
                    break


            except:
                logger(user=self.user, message='jupyter_port %s' %
                       jupyter_port, level='CRITICAL')
                logger(user=self.user, message="FUNCTION 'configure()' ENDED!", level='WARNING')
                child.close(force=True)
                break

        if jupyter_port is None:
            logger(user=self.user, message='NO RUNNING JUPYTER NOTEBOOK', level='WARNING')
        return is_user, running_jupyter, jupyter_port



    def forward(self, local_port, remote_port, running_instance):
        """Forward port of running instance from HPC to local VM.
        Start new Jupyter instance if nothing running.
        WITH A RUNNING JUPYTER INSTANCE ON A KNOWN PORT:
            - FORWARD KNOWN PORT TO GATEWAY
            - LOGIN IS SUCCESSFULL
            - LOGIN FAILED
        Update users state to 'initialized' before running this function.

        Args:
            remote_port: Port used on HPC.
            running_instance: True / False. If just forward existing running jupyter or start new jupyter.
        """
        try:
            remote_port = int(remote_port)
        except:
            logger(user=self.user, message='INVALID REMOTE PORT!', level='ERROR')
            logger(user=self.user, message="FUNCTION 'forward()' ENDED!", level='ERROR')
            # UPDATE USER IN DATABASE
            add_db(db_name=DATABASE_NAME,
                   user=self.user,
                   last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   local_port=0,
                   talon_port=0,
                   login_node=self.hostname,
                   pid_session=self.pid,
                   state_session='ended')
            return

        logger(user=self.user, message='FREE LOCAL PORT: %s'%local_port, level='INFO')
        child = pexpect.spawn('ssh -L 0.0.0.0:%s:127.0.0.1:%s  %s@%s -o StrictHostKeyChecking=no' %
                              (local_port, remote_port, self.user, self.hostname), encoding='utf-8', timeout=self.session_length, logfile=None)
        child.expect(['password: '])
        child.sendline(self.credential)
        # login staus variables
        first_line = False
        is_logged = False
        # LOOP CHECK SHELL
        while True:
            try:
                child.expect('\n')
                out_line = child.before
                logger(user=self.user, message=str(out_line), level='INFO', verbose=False)

                # FIRST LINE OF THE LOGIN
                if (" " in out_line) and not first_line:
                    first_line = True

                # LOGIN IS SUCCESSFULL
                if ("Last login:" in out_line) and first_line:
                    is_logged = True
                    logger(user=self.user, message='LOGIN TO HPC SUCCESSFULL! STARTING JUPYTER...', level='CRITICAL')
                    # CHANGE PATH
                    child.sendline("cd /storage/scratch2/%s"%(self.user))
                    # ADD ENVIROMENT VARIABLES
                    child.sendline('export PATH="$PATH:%s/bin"'%(self.conda_pah))
                    child.sendline('export PATH="$PATH:%s/lib"'%(self.conda_pah))
                    child.sendline('export PATH="$PATH:%s/bin"'%self.python_path)
                    child.sendline('export PATH="$PATH:%s/lib"'%(self.python_path))
                    child.sendline("export IPYTHONDIR=/storage/scratch2/%s/.ipython"%(self.user))
                    child.sendline("export JUPYTER_CONFIG_DIR=/storage/scratch2/%s/.jupyter"%(self.user))
                    child.sendline("export JUPYTER_DATA_DIR=/storage/scratch2/%s/.jupyter"%(self.user))
                    if running_instance is False:
                        # NEED NEW JUPYTER INSTANCE [MAKE SURE TO KEEP WATCHING OUTPUT]
                        child.sendline("nohup %s lab --no-browser --ip=0.0.0.0 --port=%s &> .jupyter_lab.log & tail -f .jupyter_lab.log"%(self.jupyter_bin_path, remote_port))

                # JUPYTER PORT FORWARDED
                if (running_instance is True) and (is_logged is True):
                    logger(user=self.user, message='JUPYTER FORWARDED. LOCAL PORT: %s REMOTE PORT: %s'%
                            (local_port, remote_port), level='CRITICAL')
                    # UPDATE USER IN DATABASE
                    add_db(db_name=DATABASE_NAME,
                           user=self.user,
                           last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           local_port=local_port,
                           talon_port=remote_port,
                           login_node=self.hostname,
                           pid_session=self.pid,
                           state_session='running')

                # JUPYTER STARTED SUCCESSFULLY
                if ('The Jupyter Notebook is running at' in out_line) and (is_logged is True):
                    logger(user=self.user, message='JUPYTER STARTED SUCCESSFULLY. LOCAL PORT: %s REMOTE PORT: %s'%
                            (local_port, remote_port), level='CRITICAL')
                    # UPDATE USER IN DATABASE
                    add_db(db_name=DATABASE_NAME,
                           user=self.user,
                           last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           local_port=local_port,
                           talon_port=remote_port,
                           login_node=self.hostname,
                           pid_session=self.pid,
                           state_session='running')

                # LOGIN FAILED
                if ("Last login:" not in out_line) and first_line and not is_logged:
                    logger(user=self.user, message='LOGIN FAILED!', level='ERROR')
                    # UPDATE USER IN DATABASE
                    add_db(db_name=DATABASE_NAME,
                           user=self.user,
                           last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           local_port=0,
                           talon_port=0,
                           login_node=0,
                           pid_session=0,
                           state_session='ended')
                    child.close(force=True)
                    break

            except:
                logger(user=self.user, message='forward_port ENDED', level='WARNING')
                # UPDATE USER IN DATABASE
                add_db(db_name=DATABASE_NAME,
                       user=self.user,
                       last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       local_port=0,
                       talon_port=0,
                       login_node=0,
                       pid_session=0,
                       state_session='ended')
                child.close(force=True)
                break
        return


def jupyter_run(conn, user, credential, hostname, conda_pah, python_path, jupyter_bin_path, session_length):
    """Functions wrapper for python multiprocessing.

    Args:
        conn: Multi-process connection.
        _euid: User id.
        _pass: Password for login to HPC.
        hostname: Hostname of HPC.
        session_timeout: Seconds until end session.
    """

    try:
        session_length = int(session_length)
    except:
        # UPDATE USER IN DATABASE
        add_db(db_name=DATABASE_NAME,
               user=user,
               last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
               local_port=0,
               talon_port=0,
               login_node=hostname,
               pid_session=0,
               state_session='ended')
        # SEND MESSAGE TO MASTER PROCESS
        conn.send('ended 0')
        conn.close()
        return

    pid = os.getpid()
    # CREATE INSTANCE
    jupyter_instance = JupyterLab(user, credential, hostname, conda_pah, python_path, jupyter_bin_path, pid, session_length)
    # CHECK CONFIGURATION
    user_exists, running_jupyter, jupyter_port = jupyter_instance.configure()

    # GRAB FREE LOCAL PORT
    free_port = find_free_port(min_port=START_OPEN_PORT, max_port=END_OPEN_PORT)

    if user_exists is True:
        if jupyter_port is not None:
            # SEND MESSAGE TO MASTER PROCESS
            conn.send('running %s'%free_port)
            conn.close()
            # FORWARD JUPYTER INSTANCE
            jupyter_instance.forward(local_port=free_port, remote_port=jupyter_port, running_instance=running_jupyter)
        else:
            logger(user=user, message='USER %s GOT UNEXPECTED ERROR!'%user, level='ERROR')
            # UPDATE USER IN DATABASE
            add_db(db_name=DATABASE_NAME,
                   user=user,
                   last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   local_port=0,
                   talon_port=0,
                   login_node=hostname,
                   pid_session=0,
                   state_session='ended')
            # SEND MESSAGE TO MASTER PROCESS
            conn.send('ended None')
            conn.close()

    else:
        logger(user=user, message='USER %s DOES NOT EXIST!'%user, level='ERROR')
        # UPDATE USER IN DATABASE
        add_db(db_name=DATABASE_NAME,
               user=user,
               last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
               local_port=0,
               talon_port=0,
               login_node=hostname,
               pid_session=0,
               state_session='ended')
        # SEND MESSAGE TO MASTER PROCESS
        conn.send('ended %s'%free_port)
        conn.close()
    return
