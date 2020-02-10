# import the Flask class from the flask module
from flask import Flask, render_template, redirect, url_for, request
import pexpect
import sys
from io import StringIO
from multiprocessing import Process, Pipe
import os
import time
import datetime



"""CHECK IF ANY RUNNING JUPYTER and HASH AND JUPYTER CONFIG [ELSE CREATE] AND USER EXISTS"""
def jupyter_port(euid, passw, addrs, timeout=5):
    ## THIS FUNCTION EXECUTES THE FOLLOWNG PROCEDURES:
    ##  - USER EXISTS:
    ##                  CHECK IF USER EXISTS
    ##                  CHECK IF jupyter_notebook_config.json EXISTS
    ##  - JUPYTER CONFIG EXISTS:
    ##                              CHECK IF JUPYTER CONFIG EXISTS
    ##                              REQUEST HASH PASSWORD SHA1
    ##  - GRAB SHA1 HASH:   CHECK IF HASH EXISTS
    ##                      REMOVE POTENTIAL jupyter_notebook_config.py FILE
    ##                      RECREATE jupyter_notebook_config.py FILE
    ##  - CONFIGURE jupyter_notebook_config.py:
    ##                                          ALLOW REMOTE ACCESS
    ##                                          TIMEOUT KILL NOTEBOOK
    ##                                          CHECK RUNNING NOTEBOOKS
    ##  - LOOKING FOR RUNNING JUPYTER INSTANCES:
    ##                                              CHECK IF RUNNING JUPYTER
    ##  - GRAB LAST RUNNING JUPYTER NOTEBOOK PORT
    ##  - CHECK IF JUPYTER CONFIG NOT EXISTS:
    ##                                  JUPYTER CONFIG NOT EXISTS AND USER EXISTS
    ##                                  JUPYTER CONFIG CREATED
    ##  - CHECK IF FOUND NEWLY CREATED JUPYTER CONFIGURATION:
    ##                                      FOUND NEWLY CREATED JUPYTER CONFIG

    print("CHECK IF ANY RUNNING JUPYTER and HASH AND JUPYTER CONFIG")
    child = pexpect.spawn('ssh %s@%s -o StrictHostKeyChecking=no' % (euid, addrs), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)

    ## SHELL COMMANDS
    shell_jupyter_config_path = "python -c \"import os; print('jupyter_config: ',os.path.exists('/home/%s/.jupyter/jupyter_notebook_config.json'))\""%(euid)
    shell_jupyter_config_sha = "awk -F\": \" '/\"password\": /{print $2;}' /home/%s/.jupyter/jupyter_notebook_config.json"%(euid)
    shell_jupyter_running = "/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook list"

    ## STAUS VARIABLES
    jupyter_sha = None
    jupyter_last_port = None

    ## STATE BOOLEAN VARIABLES
    is_jupyter_config = False
    is_user = False
    checking_running_jupyters = False
    configuring_jupyter = False

    ## JUPYTER CONFIG FILE
    allow_remote_access = "sed -i 's/#c.NotebookApp.allow_remote_access = False/c.NotebookApp.allow_remote_access = True/g' .jupyter/jupyter_notebook_config.py"
    cull_busy = "sed -i 's/#c.MappingKernelManager.cull_busy = False/c.MappingKernelManager.cull_busy = False/g' .jupyter/jupyter_notebook_config.py"
    cull_connected = "sed -i 's/#c.MappingKernelManager.cull_connected = False/c.MappingKernelManager.cull_connected = False/g' .jupyter/jupyter_notebook_config.py"
    cull_idle_timeout = "sed -i 's/#c.MappingKernelManager.cull_idle_timeout = 0/c.MappingKernelManager.cull_idle_timeout = 10/g' .jupyter/jupyter_notebook_config.py"
    cull_interval = "sed -i 's/#c.MappingKernelManager.cull_interval = 300/c.MappingKernelManager.cull_interval = 5/g' .jupyter/jupyter_notebook_config.py"
    kernel_info_timeout = "sed -i 's/#c.MappingKernelManager.kernel_info_timeout = 60/c.MappingKernelManager.kernel_info_timeout = 60/g' .jupyter/jupyter_notebook_config.py"
    shutdown_no_activity_timeout = "sed -i 's/#c.NotebookApp.shutdown_no_activity_timeout = 0/c.NotebookApp.shutdown_no_activity_timeout = 15/g' .jupyter/jupyter_notebook_config.py"

    ## LOOP CHECK SHELL
    while True:
        try:
            child.expect('\n')
            out_line = child.before
            # print("out_line", out_line)

            ## CHECK IF USER EXISTS
            if "Last login:" in out_line:
                ## USER EXISTS
                is_user = True
                print("\tUSER EXISTS")
                ## CHECK IF jupyter_notebook_config.json EXISTS
                child.sendline(shell_jupyter_config_path)

            ## CHECK IF JUPYTER CONFIG AND USER EXISTS
            if ("('jupyter_config: ', True)"  in out_line) and is_user:
                ## JUPYTER CONFIG EXISTS
                is_jupyter_config = True
                print("\tJUPYTER CONFIG EXISTS")
                ## REQUEST HASH PASSWORD SHA1
                child.sendline(shell_jupyter_config_sha)

            ## CHECK IF HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("sha1:" in out_line) and is_jupyter_config:
                ## GRAB SHA1 HASH
                print("\tGRAB SHA1 HASH")
                jupyter_sha = str(out_line.replace('"', '')).strip()
                print("\tjupyter_sha", jupyter_sha)
                ## START JUPYTER CONFIGURATION
                configuring_jupyter = True
                ## REMOVE POTENTIAL jupyter_notebook_config.py FILE
                child.sendline('rm .jupyter/jupyter_notebook_config.py')
                ## RECREATE jupyter_notebook_config.py FILE
                child.sendline('/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook --generate-config')
                print("\t\tCREATED jupyter_notebook_config.py FILE")

            ## CONFIGURE jupyter_notebook_config.py
            if "Writing default config to:" in out_line and configuring_jupyter:
                ## ALLOW REMOTE ACCESS
                child.sendline(allow_remote_access)
                ## TIMEOUT KILL NOTEBOOK
                child.sendline(cull_busy)
                child.sendline(cull_connected)
                child.sendline(cull_idle_timeout)
                child.sendline(cull_interval)
                child.sendline(kernel_info_timeout)
                child.sendline(shutdown_no_activity_timeout)
                configuring_jupyter = False
                print("\t\tJUPYTER CONFIG FILE FINISHED CONFIGURE")
                ## CHECK RUNNING NOTEBOOKS
                child.sendline(shell_jupyter_running)

            ## CHECK IF RUNNING JUPYTER and HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("Currently running servers:" in out_line) and jupyter_sha and (not configuring_jupyter):
                ## LOOKING FOR RUNNING JUPYTER INSTANCES
                checking_running_jupyters = True
                jupyter_last_port = "no_ports"
                print("\tLOOKING FOR RUNNING JUPYTER INSTANCES")

            ## GRAB LAST RUNNING JUPYTER IF RUNNING JUPYTER and HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("http://" in out_line) and checking_running_jupyters:
                ## GRAB LAST RUNNING JUPYTER PORT
                print("\tGRAB LAST RUNNING JUPYTER NOTEBOOK PORT")
                jupyter_last_port = out_line.split(":")[2].split("/")[0]
                ## STOP LOOKING FOR RUNNING JUPYTER NOTEBOOKS SERVERS
                checking_running_jupyters = False
                print("\t\tjupyter_last_port", jupyter_last_port)
                child.close(force=True)
                return is_user, is_jupyter_config, jupyter_sha, jupyter_last_port

            ## CHECK IF JUPYTER CONFIG NOT EXISTS AND USER EXISTS
            if ("('jupyter_config: ', False)" in out_line) and is_user:
                ## JUPYTER CONFIG NOT EXISTS AND USER EXISTS
                print("\tJUPYTER CONFIG NOT EXISTS AND USER EXISTS")
                ## CREATE JUPYTER PASSWORD
                child.sendline("/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook password")
                child.expect("Enter password:")
                child.sendline(passw)
                child.expect("Verify password:")
                child.sendline(passw)
                print("\t\tJUPYTER CONFIG CREATED")

            ## CHECK IF FOUND NEWLY CREATED JUPYTER CONFIGURATION
            if ("Wrote hashed password to" in out_line):
                print("\tFOUND NEWLY CREATED JUPYTER CONFIG")
                child.sendline(shell_jupyter_config_path)

        except:
            print("ENDED jupyter_port")
            child.close(force=True)
            break

    if jupyter_last_port == "no_ports":
        print("\tNO RUNNING JUPYTER NOTEBOOK")

    return is_user, is_jupyter_config, jupyter_sha, jupyter_last_port


## TEST
# is_user, is_jupyter_config, jupyter_sha, jupyter_last_port = jupyter_port(euid=euid, pass_=pass_, addrs=addrs, timeout=5)
# print("\nis_user: %s \nis_jupyter_config: %s \njupyter_sha: %s \njupyter_last_port: %s" %(is_user, is_jupyter_config, jupyter_sha, jupyter_last_port))

def run_jupyter(euid, passw, addrs, timeout=5):
    ## START JUPYTER NOTEBOOK IN BACKGROUND PROCESS
    print("STARTING JUPYTER NOTEBOOK")
    child = pexpect.spawn("ssh %s@%s -o StrictHostKeyChecking=no \"/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter lab --no-browser --ip=0.0.0.0\" &" % (euid, addrs), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)
    ## LOOP CHECK SHELL
    while True:
        try:
            child.expect('\n')
            out_line = child.before
            # print("out_line", out_line)
        except:
            print("\tRUNNING JUPYTER NOTEBOOK")
            child.close(force=True)
            break
    return


def forward_port(euid, passw, addrs, remote_port, local_port, timeout=5):
    ## WITH A RUNNING JUPYTER INSTANCE ON A KNOWN PORT:
    ##  - FORWARD KNOWN PORT TO GATEWAY
    ##  - LOGIN IS SUCCESSFULL
    ##  - LOGIN FAILED
    print("FORWARD RUNNING JUPYTER INSTANCE PORT")
    child = pexpect.spawn('ssh -L 0.0.0.0:%s:127.0.0.1:%s  %s@%s -o StrictHostKeyChecking=no' % (local_port, remote_port, euid, addrs), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)
    # login staus variables
    first_line = False
    is_logged = False
    ## LOOP CHECK SHELL
    while True:
        try:
            child.expect('\n')
            out_line = child.before
            # print("out_line", out_line)

            ## FIRST LINE OF THE LOGIN
            if (" " in out_line) and not first_line:
                first_line = True

            ## LOGIN IS SUCCESSFULL
            if ("Last login:" in out_line) and first_line:
                is_logged = True
                print("\tLOGIN IS SUCCESSFULL!")
                print("\tFORWARDING...")

            ## LOGIN FAILED
            if ("Last login:" not in out_line) and first_line and not is_logged:
                print("\tLOGIN FAILED!")
                child.close(force=True)
                break

        except:
            print("\tENDED")
            child.close(force=True)
            break
    return

# TEST
# forward_port(euid=euid, pass_=pass_, addrs=addrs, remote_port=8888, local_port=8888, timeout=10)

def jupyter_instance(_euid, _pass, hostname, session_timeout):

    is_user, is_jupyter_config, jupyter_sha, jupyter_last_port = jupyter_port(euid=_euid, passw=_pass, addrs=hostname, timeout=5)

    if is_user and is_jupyter_config and jupyter_last_port == "no_ports":
        print("NO PORTS FOUND! START JUPYTER INSTANCE")
        run_jupyter(euid=_euid, passw=_pass, addrs=hostname, timeout=5)
        _, _, _, jupyter_last_port = jupyter_port(euid=_euid, passw=_pass, addrs=hostname, timeout=5)

        if jupyter_last_port and (jupyter_last_port != "no_ports"):
            ## CHECK IF USER HAS FORWARDED PORTS
            print("FORWARD PORT")
            forward_port(euid=_euid, passw=_pass, addrs=hostname, remote_port=jupyter_last_port, local_port=jupyter_last_port, timeout=session_timeout)

    elif jupyter_last_port and (jupyter_last_port != "no_ports"):
        print("FORWARD PORT")
        forward_port(euid=_euid, passw=_pass, addrs=hostname, remote_port=jupyter_last_port, local_port=jupyter_last_port, timeout=session_timeout)

    else:
        print("COMPLETE FAIL!")
    print("\nis_user: %s \nis_jupyter_config: %s \njupyter_sha: %s \njupyter_last_port: %s" %(is_user, is_jupyter_config, jupyter_sha, jupyter_last_port))
    return


euid = ""
addrs = "vis.acs.unt.edu"
pass_ = ""
session_time = 30

jupyter_instance(_euid=euid, _pass=pass_, hostname=addrs, session_timeout=session_time)
