# import the Flask class from the flask module
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


LOGIN_NODE = 'vis.acs.unt.edu'
DATE_TEMPLATE = '%Y-%m-%d %H:%M:%S'
SESSION_TIME = 60  # seconds
DB_NAME = 'jupyter_talon_usage.db'


def find_free_port():
    """Find available port
    Args:
        available_port: Available random port. Int type.
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        available_port = s.getsockname()[1]
        return available_port


def logger(user, message, level, fname='logs.log', verbose=True):
  """Logging function

  Args:
    user: user id
    message: text needed logged
    level: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
    fname: file name to save logs
    verbose: if print to stdou

  Source: https://docs.python.org/2/howto/logging.html
  """
  time_log = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  assert level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']
  assert str(user) and str(message)
  with open(fname, 'a') as f:
    line = '%s %s %s %s'%(time_log, str(user), level, str(message))
    if verbose: print(line)
    f.write(line + '\n')
  return



def kill_pid(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def create_db(db_name):
    '''
      CREATE DATABASE IF NOT EXISTS.
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
        logger(user='root', message='DB FAILED! %s'%str(e), level='ERROR')
        print("DB FAILED!", e)
        return False


def add_db(db_name, euid, last_login, local_port, talon_port, login_node, pid_session, state_session):
    '''
      ADD INSTANCE IN DATABASE. CREATE DATABASE IF NOT EXISTS.
      COLUMNS: 'euid', 'first_login', 'last_login', 'local_port', 'talon_port', 'login_node', 'count_logins', 'pid_session', 'state_session'
      state_session:  'initiated' [login is started]
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
            logger(user=euid, message="USER %s STATE '%s'" % (euid, state_session), level='INFO')
            print("USER %s STATE '%s'" % (euid, state_session))
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
        logger(user=euid, message='\tadd_db FAILED! %s'%str(e), level='ERROR')
        print("\tadd_db FAILED!", e)
    return


def from_db(db_name, euid):
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
                logger(user=euid, message='USER %s RETRIEVED FROM DB!'%euid, level='INFO')
                print("USER %s RETRIEVED FROM DB!"%euid)
            else:
                logger(user=euid, message='EUID %s NOT ADDED TO DB!'%euid, level='WARNING')
                print('EUID %s NOT ADDED TO DB! ' % euid)
        else:
            logger(user=euid, message='DB %s does not exist!'%db_name, level='WARNING')
            print("DB %s does not exist!" % db_name)
    except Exception as e:
        logger(user=euid, message='from_db FAILED! %s'%str(e), level='ERROR')
        print("from_db FAILED!", e)
    return row


"""CHECK IF ANY RUNNING JUPYTER and HASH AND JUPYTER CONFIG [ELSE CREATE] AND USER EXISTS"""


def jupyter_port(euid, passw, addrs, running_pid, timeout=5):
    # THIS FUNCTION EXECUTES THE FOLLOWNG PROCEDURES:
    # - USER EXISTS:
    # CHECK IF USER EXISTS
    # CHECK IF jupyter_notebook_config.json EXISTS
    # - JUPYTER CONFIG EXISTS:
    # CHECK IF JUPYTER CONFIG EXISTS
    # REQUEST HASH PASSWORD SHA1
    # - GRAB SHA1 HASH:   CHECK IF HASH EXISTS
    # REMOVE POTENTIAL jupyter_notebook_config.py FILE
    # RECREATE jupyter_notebook_config.py FILE
    # - CONFIGURE jupyter_notebook_config.py:
    # ALLOW REMOTE ACCESS
    # TIMEOUT KILL NOTEBOOK
    # CHECK RUNNING NOTEBOOKS
    # - LOOKING FOR RUNNING JUPYTER INSTANCES:
    # CHECK IF RUNNING JUPYTER
    # - GRAB LAST RUNNING JUPYTER NOTEBOOK PORT
    # - CHECK IF JUPYTER CONFIG NOT EXISTS:
    # JUPYTER CONFIG NOT EXISTS AND USER EXISTS
    # JUPYTER CONFIG CREATED
    # - CHECK IF FOUND NEWLY CREATED JUPYTER CONFIGURATION:
    # FOUND NEWLY CREATED JUPYTER CONFIG

    logger(user=euid, message='CHECK IF ANY RUNNING JUPYTER and HASH AND JUPYTER CONFIG', level='INFO')
    print("CHECK IF ANY RUNNING JUPYTER and HASH AND JUPYTER CONFIG")
    # UPDATE USER IN DATABASE
    add_db( db_name=DB_NAME,
            euid = euid,
            last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            local_port = 0,
            talon_port = 0,
            login_node = LOGIN_NODE,
            pid_session = running_pid,
            state_session = 'initiated')

    child = pexpect.spawn('ssh %s@%s -o StrictHostKeyChecking=no' %
                          (euid, addrs), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)

    # SHELL COMMANDS
    shell_jupyter_config_path = "python -c \"import os; print('jupyter_config: ',os.path.exists('/home/%s/.jupyter/jupyter_notebook_config.json'))\"" % (
        euid)
    shell_jupyter_config_sha = "awk -F\": \" '/\"password\": /{print $2;}' /home/%s/.jupyter/jupyter_notebook_config.json" % (
        euid)
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
    shutdown_no_activity_timeout = "sed -i 's/#c.NotebookApp.shutdown_no_activity_timeout = 0/c.NotebookApp.shutdown_no_activity_timeout = 15/g' .jupyter/jupyter_notebook_config.py"

    # LOOP CHECK SHELL
    while True:
        try:
            child.expect('\n')
            out_line = child.before
            logger(user=euid, message=str(out_line), level='INFO', verbose=False)
            # print("out_line", out_line)

            # CHECK IF USER EXISTS
            if "Last login:" in out_line:
                # USER EXISTS
                is_user = True
                logger(user=euid, message='\tUSER EXISTS', level='INFO')
                print("\tUSER EXISTS")
                # CHECK IF jupyter_notebook_config.json EXISTS
                child.sendline(shell_jupyter_config_path)

            # CHECK IF JUPYTER CONFIG AND USER EXISTS
            if ("('jupyter_config: ', True)" in out_line) and is_user:
                # JUPYTER CONFIG EXISTS
                is_jupyter_config = True
                logger(user=euid, message='\tJUPYTER CONFIG EXISTS', level='INFO')
                print("\tJUPYTER CONFIG EXISTS")
                # REQUEST HASH PASSWORD SHA1
                child.sendline(shell_jupyter_config_sha)

            # CHECK IF HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("sha1:" in out_line) and is_jupyter_config:
                # GRAB SHA1 HASH
                logger(user=euid, message='\tGRAB SHA1 HASH', level='INFO')
                print("\tGRAB SHA1 HASH")
                jupyter_sha = str(out_line.replace('"', '')).strip()
                logger(user=euid, message='\tjupyter_sha', level='INFO')
                print("\tjupyter_sha", jupyter_sha)
                # START JUPYTER CONFIGURATION
                configuring_jupyter = True
                # REMOVE POTENTIAL jupyter_notebook_config.py FILE
                child.sendline('rm .jupyter/jupyter_notebook_config.py')
                # RECREATE jupyter_notebook_config.py FILE
                child.sendline(
                    '/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook --generate-config')
                logger(user=euid, message='\t\tCREATED jupyter_notebook_config.py FILE', level='INFO')
                print("\t\tCREATED jupyter_notebook_config.py FILE")

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
                logger(user=euid, message='\t\tJUPYTER CONFIG FILE FINISHED CONFIGURE', level='INFO')
                print("\t\tJUPYTER CONFIG FILE FINISHED CONFIGURE")
                # CHECK RUNNING NOTEBOOKS
                child.sendline(shell_jupyter_running)

            # CHECK IF RUNNING JUPYTER and HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("Currently running servers:" in out_line) and jupyter_sha and (not configuring_jupyter):
                # LOOKING FOR RUNNING JUPYTER INSTANCES
                checking_running_jupyters = True
                jupyter_last_port = "no_ports"
                logger(user=euid, message='\tLOOKING FOR RUNNING JUPYTER INSTANCES', level='INFO')
                print("\tLOOKING FOR RUNNING JUPYTER INSTANCES")

            # GRAB LAST RUNNING JUPYTER IF RUNNING JUPYTER and HASH AND JUPYTER CONFIG AND USER EXISTS
            if ("http://" in out_line) and checking_running_jupyters:
                # GRAB LAST RUNNING JUPYTER PORT
                logger(user=euid, message='\tGRAB LAST RUNNING JUPYTER NOTEBOOK PORT', level='INFO')
                print("\tGRAB LAST RUNNING JUPYTER NOTEBOOK PORT")
                jupyter_last_port = out_line.split(":")[2].split("/")[0]
                # STOP LOOKING FOR RUNNING JUPYTER NOTEBOOKS SERVERS
                checking_running_jupyters = False
                logger(user=euid, message='\t\tjupyter_last_port %s'%jupyter_last_port, level='INFO')
                print("\t\tjupyter_last_port", jupyter_last_port)
                child.close(force=True)
                return is_user, is_jupyter_config, jupyter_sha, jupyter_last_port

            # CHECK IF JUPYTER CONFIG NOT EXISTS AND USER EXISTS
            if ("('jupyter_config: ', False)" in out_line) and is_user:
                # JUPYTER CONFIG NOT EXISTS AND USER EXISTS
                logger(user=euid, message='\tJUPYTER CONFIG NOT EXISTS AND USER EXISTS', level='INFO')
                print("\tJUPYTER CONFIG NOT EXISTS AND USER EXISTS")
                # CREATE JUPYTER PASSWORD
                child.sendline(
                    "/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter notebook password")
                child.expect("Enter password:")
                child.sendline(passw)
                child.expect("Verify password:")
                child.sendline(passw)
                logger(user=euid, message='\t\tJUPYTER CONFIG CREATED', level='INFO')
                print("\t\tJUPYTER CONFIG CREATED")

            # CHECK IF FOUND NEWLY CREATED JUPYTER CONFIGURATION
            if ("Wrote hashed password to" in out_line):
                print("\tFOUND NEWLY CREATED JUPYTER CONFIG")
                child.sendline(shell_jupyter_config_path)

        except:
            logger(user=euid, message='\tjupyter_port ENDED!', level='WARNING')
            print("\tjupyter_port ENDED!")
            child.close(force=True)
            break

    if jupyter_last_port == "no_ports":
        logger(user=euid, message='\tNO RUNNING JUPYTER NOTEBOOK', level='WARNING')
        print("\tNO RUNNING JUPYTER NOTEBOOK")

    return is_user, is_jupyter_config, jupyter_sha, jupyter_last_port


""" START JUPYTER INSTANCE """


def run_jupyter(euid, passw, addrs, timeout=5):
    # START JUPYTER NOTEBOOK IN BACKGROUND PROCESS
    logger(user=euid, message='STARTING JUPYTER NOTEBOOK', level='INFO')
    print("STARTING JUPYTER NOTEBOOK")
    child = pexpect.spawn("ssh %s@%s -o StrictHostKeyChecking=no \"/cm/shared/utils/PYTHON/ANACONDA/5.2/bin/jupyter lab --no-browser --ip=0.0.0.0\" &" %
                          (euid, addrs), encoding='utf-8', timeout=timeout, logfile=None)
    child.expect(['password: '])
    child.sendline(passw)
    # LOOP CHECK SHELL
    while True:
        try:
            child.expect('\n')
            out_line = child.before
            # print("out_line", out_line)
        except:
            logger(user=euid, message='\tRUNNING JUPYTER NOTEBOOK', level='INFO')
            print("\tRUNNING JUPYTER NOTEBOOK")
            child.close(force=True)
            break
    return


""" FORWARD PORT """


def forward_port(euid, passw, addrs, remote_port, local_port, running_pid, timeout=5):
    # WITH A RUNNING JUPYTER INSTANCE ON A KNOWN PORT:
    # - FORWARD KNOWN PORT TO GATEWAY
    # - LOGIN IS SUCCESSFULL
    # - LOGIN FAILED
    logger(user=euid, message='FORWARD RUNNING JUPYTER INSTANCE PORT', level='INFO')
    print("FORWARD RUNNING JUPYTER INSTANCE PORT")
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
                logger(user=euid, message='\tLOGIN IS SUCCESSFULL! FORWARDING...', level='CRITICAL')
                print("\tLOGIN IS SUCCESSFULL! FORWARDING...")
                # UPDATE USER DATABASE
                add_db( db_name=DB_NAME,
                        euid = euid,
                        last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        local_port = local_port,
                        talon_port = remote_port,
                        login_node = LOGIN_NODE,
                        pid_session = running_pid,
                        state_session = 'running')

            # LOGIN FAILED
            if ("Last login:" not in out_line) and first_line and not is_logged:
                logger(user=euid, message='\tLOGIN FAILED!', level='ERROR')
                print("\tLOGIN FAILED!")
                # UPDATE USER DATABASE
                add_db( db_name=DB_NAME,
                        euid = euid,
                        last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        local_port = local_port,
                        talon_port = remote_port,
                        login_node = LOGIN_NODE,
                        pid_session = running_pid,
                        state_session = 'ended')
                child.close(force=True)
                break

        except:
            logger(user=euid, message='\tforward_port ENDED', level='WARNING')
            print("\tforward_port ENDED")
            # UPDATE USER INFO
            add_db( db_name=DB_NAME,
                    euid = euid,
                    last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    local_port = local_port,
                    talon_port = remote_port,
                    login_node = LOGIN_NODE,
                    pid_session = running_pid,
                    state_session = 'ended')
            child.close(force=True)
            break
    return


""" CHECK USER ON TALON AND FORWARD PORT OF JUPYTER INSTANCE """


def jupyter_instance(conn, _euid, _pass, hostname, session_timeout):
    pid_session = os.getpid()

    is_user, is_jupyter_config, jupyter_sha, jupyter_last_port = jupyter_port(
        euid=_euid, passw=_pass, addrs=hostname, running_pid=pid_session, timeout=5)

    if is_user and is_jupyter_config and jupyter_last_port == "no_ports":
        logger(user=_euid, message='NO PORTS FOUND! START JUPYTER INSTANCE', level='WARNING')
        print("NO PORTS FOUND! START JUPYTER INSTANCE")
        run_jupyter(euid=_euid, passw=_pass, addrs=hostname, timeout=5)
        _, _, _, jupyter_last_port = jupyter_port(
            euid=_euid, passw=_pass, running_pid=pid_session, addrs=hostname, timeout=5)

        if jupyter_last_port and (jupyter_last_port != "no_ports"):
            logger(user=_euid, message='FORWARD PORT', level='INFO')
            print("FORWARD PORT")
            # send message
            random_local_port = find_free_port()
            send_line = "running %s %s %s" % (jupyter_last_port, random_local_port, pid_session)
            conn.send(send_line)
            conn.close()
            forward_port(euid=_euid, passw=_pass, addrs=hostname, remote_port=jupyter_last_port,
                         local_port=random_local_port, timeout=session_timeout, running_pid=pid_session)

    elif jupyter_last_port and (jupyter_last_port != "no_ports"):
        logger(user=_euid, message='FORWARD PORT', level='INFO')
        print("FORWARD PORT")
        # send message
        random_local_port = find_free_port()
        send_line = "running %s %s %s" % (jupyter_last_port, random_local_port, pid_session)
        conn.send(send_line)
        conn.close()
        forward_port(euid=_euid, passw=_pass, addrs=hostname, remote_port=jupyter_last_port,
                     local_port=random_local_port, timeout=session_timeout, running_pid=pid_session)

    else:
        logger(user=_euid, message='COMPLETE FAIL!', level='ERROR')
        print("COMPLETE FAIL!")
        # send message
        send_line = "ended %s %s" % (jupyter_last_port, pid_session)
        conn.send(send_line)
        conn.close()
    return


# create the application object
app = Flask(__name__)

# use decorators to link the function to a url
@app.route('/', methods=['GET', 'POST'])
def home():
    '''
        - CHECK IF USER WAS EVER LOGGED IN. IF NOT START USER FROM SCRATCH.
        ADD USER IN DATABASE WITH RUNNING INSTANCE.
        - FOR RETURNING USER CHECK THE INSTANCE STATUS.
        FOR INITIATED INSTANCES AVOID RE-RUNNING PROCESSES.
        KEEP CHECKING STATE FOR 1 MINUT. IF NO CHANGE CONSIDER INSTANCE ENDED AND RE-START.
        IF STATE CHANGES - RE-FRESH CONNECITON FROM GATEWAY TO TALON.
    '''
    error = None
    if request.method == 'POST':
        use = request.form['username']
        pas = request.form['password']

        logger(user='root', message="request method 'POST' for %s"%use, level='INFO')
        # CHECK IF EUID ALREADY INITIATED
        euid_log = from_db(db_name=DB_NAME, euid=use)

        # USER NEVER LOGGED IN
        if euid_log is None:
            # UPDATE USER IN DATABASE
            add_db( db_name=DB_NAME,
                    euid = use,
                    last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    local_port = 0,
                    talon_port = 0,
                    login_node = LOGIN_NODE,
                    pid_session = 0,
                    state_session = 'initiated')

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
                add_db( db_name=DB_NAME,
                        euid = use,
                        last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        local_port = jupyter_last_port,
                        talon_port = jupyter_last_port,
                        login_node = LOGIN_NODE,
                        pid_session = pid_session,
                        state_session = state_session)
                error = 'Invalid Credentials. Please try again.'
                logger(user=use, message=error, level='ERROR')
                return render_template('login.html', error=error)
            else:
                # connection is successfull - forward to jupyter
                ide_link = "http://hpc-gateway.hpc.unt.edu:%s" % (
                    random_local_port)
                # update user database
                add_db( db_name=DB_NAME,
                        euid = use,
                        last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        local_port = jupyter_last_port,
                        talon_port = jupyter_last_port,
                        login_node = LOGIN_NODE,
                        pid_session = pid_session,
                        state_session = state_session)
                # return render_template('login.html', ide_link=ide_link, ide_password="Your Talon Password")
                time.sleep(5)
                logger(user=use, message='connection is successfull - forward to jupyter', level='INFO')
                return redirect(ide_link)

        # USER IN PROCESS OF LOGGING IN
        elif euid_log['state_session'] == 'initiated':
            print('LOGIN ALREADY INITIATED!')
            # connection failed
            error = 'Login Already Initiated!'
            logger(user=use, message=error, level='WARNING')
            return render_template('login.html', error=error)
        # # CHECK STATE OF EUID
        #     # JUPYTER INITIATED - MAKE USER WAIT UNTIL CHANGE STATE
        #     for _ in range(3):
        #         # WAIT 20 SECONDS BEFORE LOOKING AGAIN AT STATE
        #         time.sleep(20)
        #         euid_log = from_db(db_name=DB_NAME, euid=use)
        #         if euid_log['state_session'] != 'initiated':
        #             # STATE CHANGED - TRY START SESSION
        #             break
        #     # CHECK SATE AGAIN FOR CHANGES
        #     euid_log = from_db(db_name=DB_NAME, euid=use)

        elif (euid_log['state_session'] == 'running') or (euid_log['state_session'] == 'ended'):
            # RUN JUPYTER SEQUENCE:
            # KILL PREVIOUS PID
            kill_pid(pid=euid_log['pid_session'])
            # UPDATE USER IN DATABASE
            add_db( db_name=DB_NAME,
                    euid = use,
                    last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    local_port = 0,
                    talon_port = 0,
                    login_node = LOGIN_NODE,
                    pid_session = 0,
                    state_session = 'initiated')

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
            add_db( db_name=DB_NAME,
                    euid = use,
                    last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    local_port = jupyter_last_port,
                    talon_port = jupyter_last_port,
                    login_node = LOGIN_NODE,
                    pid_session = pid_session,
                    state_session = state_session)

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
                logger(user=use, message='connection is successfull - forward to jupyter', level='INFO')
                return redirect(ide_link)

        # else:
        #     print('FORCE KILL INSTANCE - WAITING TOO LONG')
        #     # KILL PREVIOUS PID
        #     kill_pid(pid=euid_log['pid_session'])
        #     state_session = 'ended'
        #     error = 'Something went wrong!'
        #     return render_template('login.html', error=error)



    return render_template('login.html', login='login')


# start the server with the 'run()' method
if __name__ == '__main__':
    # CHECK LOGS FOLDER
    # CHECK DB
    if create_db(db_name=DB_NAME):
        print(' * Databased checked!')
        app.run(host='0.0.0.0', debug=True, threaded=True)
    else:
        print('Database failed!')
