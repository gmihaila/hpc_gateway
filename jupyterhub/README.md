# JupyterHub

## Start Jupyter Hub:
```bash
$ PATH=$PATH:/home/george/nodejs/bin/
$ PATH=$PATH:/cm/shared/utils/GCC/6.3.0/bin
$ LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/cm/shared/utils/GCC/6.3.0/lib:/cm/shared/utils/GCC/6.3.0/lib64:w
$ /cm/shared/utils/PYTHON/jupyterhub/bin/jupyterhub -f /cm/shared/utils/PYTHON/jupyterhub/etc/jupyterhub/jupyterhub_config.py
```

## Install JupyterHub and JupyterLab from the ground up:

* Use main link [here](https://jupyterhub.readthedocs.io/en/stable/installation-guide-hard.html).
* Documentation [here](https://jupyterhub.readthedocs.io/en/0.7.2/index.html).
* Setting default url to home directory [here](https://github.com/jupyterhub/jupyterhub/issues/929).
* Troubleshooting [here](https://jupyterhub.readthedocs.io/en/latest/troubleshooting.html#error-after-spawning-my-single-user-server)


## Steps followed for Talon:

### Install nodejs and npm from source [here](https://nodejs.org/en/download/):
  * Already compiled: `PATH=$PATH:/home/george/nodejs/bin/`
  * Need to have loaded: `module load gcc/6.3.0`.
  * JupyterHub proxy: `npm install -g configurable-http-proxy`

### In case need to find and kill any running jupyterhub process:
  * See process to kill: `ps aux | grep jupyterhub`.
  * Kill process: `kill -9 PID`.
  
### Compile Python:
  * Download certain verion from [here](https://www.python.org).
  * Commands:
  ```bash
  $ vim Modules/Setup.dist
  
  /cm/shared/utils/OPENSSL/1.1.1/ssl
  export PKG_CONFIG_PATH=/cm/shared/utils/LIBFFI/lib/pkgconfig/
  pkg-config --cflags libffi
  LDFLAGS=pkg-config --libs-only-L libffi ./configure --prefix=/cm/shared/utils/PYTHON/jupyterhub --with-ensurepip=install
  ```
  
### JupyterHub:
  * use: `/cm/shared/utils/PYTHON/jupyterhub/`
  ```bash
  $ mkdir -p /cm/shared/utils/PYTHON/jupyterhub/etc/jupyterhub/

  $ cd /cm/shared/utils/PYTHON/jupyterhub/etc/jupyterhub/

  $ /cm/shared/utils/PYTHON/jupyterhub/bin/jupyterhub --generate-config

  $ vim /cm/shared/utils/PYTHON/jupyterhub/etc/jupyterhub/jupyterhub_config.py

  c.Spawner.default_url = '/lab'
  c.JupyterHub.hub_bind_url = 'http://127.0.0.1:8082'
  c.JupyterHub.cookie_secret_file = '/srv/jupyterhub/jupyterhub_cookie_secret'
  c.JupyterHub.db_url = '/srv/jupyterhub/jupyterhub.sqlite'
  c.Spawner.cmd = ['/cm/shared/utils/PYTHON/jupyterhub/bin/jupyterhub-singleuser']
  c.Spawner.notebook_dir = '/storage/scratch2/%U'
  c.JupyterHub.extra_log_file = '/var/log/jupyterhub.log'
  # add this extra
  c.PAMAuthenticator.open_sessions = False
  ```
  
  * System services:
  ```bash
  $ mkdir -p /cm/shared/utils/PYTHON/jupyterhub/etc/systemd
  $ vim /cm/shared/utils/PYTHON/jupyterhub/etc/systemd/jupyterhub.service

  [Unit]
  Description=JupyterHub
  After=syslog.target network.target

  [Service]
  User=root
  Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/opt/ibutils/bin:/opt/dell/srvadmin/bin:/opt/dell/srvadmin/sbin:/root/bin:/cm/shared/utils/PYTHON/jupyterhub/bin:/home/george/nodejs/bin"
  ExecStart=/cm/shared/utils/PYTHON/jupyterhub/bin/jupyterhub -f /cm/shared/utils/PYTHON/jupyterhub/etc/jupyterhub/jupyterhub_config.py

  [Install]
  WantedBy=multi-user.target

  $ systemctl enable /cm/shared/utils/PYTHON/jupyterhub/etc/systemd/jupyterhub.service
  $ systemctl daemon-reload
  $ systemctl start jupyterhub.service
  ```
