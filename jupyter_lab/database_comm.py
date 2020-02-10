import os
import sqlite3
import os
from datetime import datetime


def seconds_elapsed(previous_date, date_template):
  now = datetime.now().strftime(date_template)
  now_time = datetime.strptime(now, date_template)

  previous_time = datetime.strptime(previous_date, date_template)

  elapsed_time = (now_time - previous_time).total_seconds()

  return elapsed_time



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
    print("DB FAILED!", e)
    return False


def add_db(db_name, euid, last_login, local_port, talon_port, login_node, pid_session, state_session):
  '''
    ADD INSTANCE IN DATABASE
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
    # CHECK IF DB EXISTS
    if os.path.isfile(db_name):
      # DB EXISTS - JUST ESTABLISH CONNECTION
      print('DataBase %s found!' % db_name)
      # CONNECT TO DB
      conn = sqlite3.connect(db_name)
      # DB CONNECTION
      c = conn.cursor()
    else:
      # DB DOES NOT EXIST
      print("DataBase %s NOT found! Please run: 'create_db(db_name)'" % db_name)
      return

    # CHECK IF EUID ALREADY EXISTS
    euids = list(c.execute('SELECT euid FROM jupyter_talon ORDER BY euid').fetchall())
    if (euid,) in euids:
      # EUID ALREADY IN DB
      print('USER IN DB')
      # GRAB NUMBER OF LOGINS
      count_logins = (c.execute('SELECT count_logins FROM jupyter_talon WHERE euid=?',(euid,)).fetchall())[0][0]
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
                                          state_session=? WHERE euid=?',(
                                          last_login,
                                          local_port,
                                          talon_port,
                                          login_node,
                                          count_logins,
                                          pid_session,
                                          state_session,
                                          euid))
    else:
      # EUID NOT IN DB
      # ADD EUID IN DB
      first_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      c.execute('INSERT INTO jupyter_talon VALUES (?,?,?,?,?,?,?,?,?)',(euid,
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
    print("DB FAILED!", e)
  return


def from_db(db_name, euid):
  row = None
  columns = ['first_login', 'last_login', 'local_port', 'talon_port', 'login_node', 'count_logins', 'pid_session', 'state_session']
  try:
    # CHECK IF DB EXISTS OR NOT
    if os.path.isfile(db_name):
      # CONNECT TO DB
      conn = sqlite3.connect(db_name)
      # DB CONNECTION
      c = conn.cursor()
      # CHECK IF EUID EXISTS
      euids = list(c.execute('SELECT euid FROM jupyter_talon ORDER BY euid').fetchall())
      if (euid,) in euids:
        # EXTRACT ROW
        row = list(c.execute('SELECT first_login,\
                                    last_login,\
                                    local_port,\
                                    talon_port,\
                                    login_node,\
                                    count_logins,\
                                    pid_session,\
                                    state_session FROM jupyter_talon WHERE euid=?',(euid,)).fetchall())
        # DICTIONARY FORMAT
        row = {k:v for k,v in zip(columns, row[0])}
      else:
        print('EUID %s NOT ADDED TO DB! ' % euid)
    else:
      print("DB %s does not exist!" % db_name)
  except Exception as e:
    print("DB FAILED!", e)
  return row



db_name = 'jupyter_talon_usage.db'

create_db(db_name=db_name)

add_db( db_name='jupyter_talon_usage.db',
        euid = 'gm0234',
        last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        local_port = 8888,
        talon_port = 8888,
        login_node = 'vis.acs.unt.edu',
        pid_session = 356,
        state_session = 'running')


euid_log = from_db(db_name=db_name, euid='gm0234')

print(euid_log)
