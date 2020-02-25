# Jupyter Lab Python Server



## Debugging:
  * Local debugging instance with NGINX running to proxy port 8000:
  
  `$ flask run -h localhost -p 8000 --with-threads`

  * Using Gunicorn:
  
  `$ gunicorn -b localhost:8000 -w 1 jupyter_lab:app`

  * Simple local debugging:
  
  `$ flask run -h 0.0.0.0 --with-threads`

## Notes:
  * User side debugging:
    Check `.jupyter_lab.log` log file in jupyter running directory on HPC.

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
  $ vim /etc/nginx/sites-enabled/jupyter_lab
  ```

  Copy:
  ```
  server {
    # listen on port 80 (http)
    listen 80;
    server_name _;
    location / {
        # redirect any requests to the same URL but on https
        return 301 https://$host$request_uri;
    }
  }
  server {
    # listen on port 443 (https)
    listen 443 default_server ssl;
    server_name _;

    # location of the self-signed SSL certificate
    ssl on;
    ssl_certificate /certs/jupyterlab_hpc_unt_edu_cert.cer;
    ssl_certificate_key /certs/jupyterlab_hpc_unt_edu.key;

    # write access and error logs to
    access_log /var/log/jupyter_lab_access.log;
    error_log /var/log/jupyter_lab_error.log;
    location / {
        # forward application requests to the gunicorn server
        proxy_pass http://localhost:8000;
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        # handle static files directly, without forwarding to the application
        alias /home/george/hpc_gateway/jupyter_lab/jupyter_lab/static;
        expires 30d;
    }
  }
  ```
  Get `jupyterlab_hpc_unt_edu_cert.cer` from email confirmation to download. The `jupyterlab_hpc_unt_edu.key` should be already on the server.

  To check NGINX:
  * Check any errors that don't let NGINX start: `$ sudo nginx -t -c /etc/nginx/nginx.conf`

## Setup Python Environment:
  * Make sure python3 is installed.
  * Install virtualenv:
  ```
  $ apt-get update
  $ apt-get install python-virtualenv
  ```
  * Find path of python using `which python3`.
  * Create environment:
  ```
  $ virtualenv -p path/to/python ~/flask_env
  $ source ~/flask_env/bin/activate
  $ pip install -r requirements.txt
  ```

## Setup [Supervisor](http://supervisord.org/):
  * Have the server running in the background, and have it under constant monitoring, because if for any reason the server crashes and exits, I want to make sure a new server is automatically started to take its place. And I also want to make sure that if the machine is rebooted, the server runs automatically upon startup, without me having to log in and start things up myself.
  * I used [this](https://rcwd.dev/long-lived-python-scripts-with-supervisor.html) and [this](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xvii-deployment-on-linux) as guidance.
  * Installing Supervisor:

    ```bash
    $ sudo apt install supervisor
    [root]$ echo_supervisord_conf > /etc/supervisord.conf
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

    And add following these lines:

    ```bash
    [program:jupyter_lab]
    command=~/flask_env/bin/gunicorn -b localhost:8000 -w 4 jupyter_lab:app
    directory=~/hpc_gateway/jupyter_lab
    user=your_user
    autostart=true
    autorestart=true
    stopasgroup=true
    killasgroup=true
    ```

    Jump back into `supervisorctl` (don't forget to sudo).

    We need to run a couple of commands in Supervisor. First we need to `reread` to load the new config file. Then we need to `add jupyter_lab` to add and start it.
    Finally we'll check the `status` of the job.

## How to Stop flask server:
  * Login to VM and stop the jupyter_lab supervisor process:
    ```
    $ sudo supervisorctl
    > stop jupyter_lab
    > remove jupyter_lab
    > exit
    ```
  * Perform any debugging / maintenance / git pull.
  * When finished, start flask server.

## Start flask server:
  * Login to VM and start the supervisor process:
  ```
  $ sudo supervisorctl
  > reread
  > add jupyter_lab
  > exit
  ```

## Firewall `ufw`:
  * Install firewall if not already:
  `$ sudo apt install ufw`
  * Add http nginx aplicaiton to `ufw`:
  `$ sudo vim /etc/ufw/applications.d/nginx-https`
    And copy:
    ```
    [Nginx HTTP]
    title=Web Server (HTTP)
    description=for serving web
    ports=80/tcp
    ```
  * Add https nginx aplicaiton to `ufw`:
  `$ sudo vim /etc/ufw/applications.d/nginx-https`
    And copy:
    ```
    [Nginx HTTPS]
    title=Web Server (HTTPS)
    description=for serving web
    ports=443/tcp
    ```
  * Look for applications and allow them:
    ```
    $ sudo ufw app list
    $ sudo ufw allow 'Nginx HTTP'
    $ sudo ufw allow 'Nginx HTTPS'
    ```

  * Set range of open ports:
    `$ sudo ufw allow 8999:10001/tcp`

  * Allow port for database:
    `$ sudo ufw allow 8080`
