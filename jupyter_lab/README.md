# Jupyter Lab Python Server


## Notes:
  * User side debugging:
    Check `.jupyter_lab.log` log file in jupyter running directory on HPC.

  * Test Server:
    Local debugging instance:
    `$ flask run -h 0.0.0.0 --with-threads`

    Using Gunicorn:
    `$ gunicorn -b localhost:8000 -w 1 jupyter_lab:app`


## Setup python virtual environment:
  * Regular python environment using `virtualenv`.
  * Install needed libraries:
    `$ pip install -r requirements.txt`


## Deploy Flask App:
  * Used [this](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xvii-deployment-on-linux) tutorial.

## Setup nginx server:
  * Install nginx:
  ```bash
  $ sudo apt-get update
  $ sudo apt-get install nginx -y
  $ sudo /etc/init.d/nginx stop
  $ sudo rm /etc/nginx/sites-enabled/default
  $ cd /etc/nginx/sites-enabled/
  $ vim jupyter_lab
  ```
  Make sure to set `ssl off;`


## Setup [Supervisor](http://supervisord.org/):
  * Have the server running in the background, and have it under constant monitoring, because if for any reason the server crashes and exits, I want to make sure a new server is automatically started to take its place. And I also want to make sure that if the machine is rebooted, the server runs automatically upon startup, without me having to log in and start things up myself.
  * I used [this](https://rcwd.dev/long-lived-python-scripts-with-supervisor.html) and [this](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xvii-deployment-on-linux) as guidance.
  * Installing Supervisor:

    ```bash
    $ pip install supervisor
    $ echo_supervisord_conf > /etc/supervisord.conf
    $ sudo mkdir /etc/supervisor.d
    $ sudo vim /etc/supervisord.conf
    ```

    Scroll to the very end of the file and look for the lines:

    ```bash
    ;[include]
    ;files = relative/directory/*.ini
    ```

    We want to uncomment (remove the semicolon), and update these lines to use the directory we just created:

    ```bash
    [include]
    files = /etc/supervisor.d/*.ini
    ```

  * Starting Supervisor on Boot

    ```bash
    $ sudo touch /lib/systemd/system/supervisord.service
    $ sudo vim /lib/systemd/system/supervisord.service
    ```

    Copy the the above onto your clipboard and paste it into our new service file:

    ```bash
    # supervisord service for systemd
    # Based on config by ET-CS (https://github.com/ET-CS)
    [Unit]
    Description=Supervisor daemon

    [Service]
    Type=forking
    ExecStart=/usr/local/bin/supervisord
    ExecStop=/usr/local/bin/supervisorctl $OPTIONS shutdown
    ExecReload=/usr/local/bin/supervisorctl $OPTIONS reload
    KillMode=process
    Restart=on-failure
    RestartSec=42s

    [Install]
    WantedBy=multi-user.target
    ```
    Finally we can load and start the service:

    ```bash
    $ sudo systemctl daemon-reload
    $ sudo systemctl enable supervisord.service
    $ sudo systemctl start supervisord.service
    ```

    If everything has gone according to plan then great! If not, check the output of `$ sudo journalctrl -xe` for hints on what's gone wrong ... and fix it!

  * Connect & Test
    Start by connecting to Supervisor using the command:

    ```bash
    sudo supervisorctl
    ```

  * Supervisor Program

    Supervisor jobs or processes are referred to as Programs and are defined using a simple syntax either in the main Supervisor config file or via individual files.

    Let's make a new file in our /etc/supervisor.d/ directory so we can load it:

    ```bash
    $ sudo vim /etc/supervisor.d/jupyter_lab.ini
    ```

    Jump back into `supervisorctl` (don't forget to sudo).

    We need to run a couple of commands in Supervisor. First we need to `reread` to load the new config file. Then we need to `add jupyter_lab` to add and start it.

    Finally we'll check the `status` of the job.
