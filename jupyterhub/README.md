<p align="center">
 <img width="400" height="140" src="https://jupyterhub.readthedocs.io/en/stable/_static/logo.png" alt="text" >
</p>

## Start Jupyter Hub:
```bash
$ PATH=$PATH:/cm/shared/utils/NODE/12.16.1/bin/
$ export PATH="/cm/shared/utils/GCC/6.3.0/bin:$PATH"
```
Or all in one:
```bash
$ export PATH="/cm/shared/utils/NODE/12.16.1/bin/:/cm/shared/utils/GCC/6.3.0/bin:$PATH"
```
And rest of them:
```bash
$ export LD_LIBRARY_PATH="/cm/shared/utils/GCC/6.3.0/lib:/cm/shared/utils/GCC/6.3.0/lib64"
$ /opt/jupyterhub/bin/jupyterhub -f /opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py
```

## Add Kernels:
* Single-user env is `/cm/shared/utils/PYTHON/3.6.5/bin/python`
* Transformers: `/cm/shared/utils/PYTHON/transformers/bin/python -m ipykernel install --prefix=/cm/shared/utils/PYTHON/3.6.5/ --name 'transformers' --display-name "Transformers"`
* Anaconda: `/cm/shared/utils/PYTHON/ANACONDA/5.2/envs/beakerx/bin/python -m ipykernel install --prefix=/cm/shared/utils/PYTHON/3.6.5/ --name 'anaconda' --display-name "Anaconda"`
* H2o4gpu: `/cm/shared/utils/PYTHON/h2o4gpu-0.3.2/bin/python -m ipykernel install --prefix=/cm/shared/utils/PYTHON/3.6.5/ --name 'h2o4gpu' --display-name "H2o4gpu"`

## Setup folders:
* Follow [this](https://jupyterhub.readthedocs.io/en/0.7.2/getting-started.html#folders-and-file-locations).
* `/opt/jupyterhub` for python environemnts.
* `/opt/jupyterhub/etc/jupyterhub/` for all configuration files.
* `/srv/jupyterhub` for all security and runtime files.
* `/var/log` for log files.

## Perform maintanance when Systemd service is running:
* Stop Service: `systemctl stop jupyterhub.service`
* Check status if stopped: `systemctl status jupyterhub.service -l`
* Perform maintanance.
* Start service back up: `systemctl restart jupyterhub.service`

## Install JupyterHub and JupyterLab from the ground up:
* MAKE SURE TO [FIX](https://blog.jupyter.org/security-fix-for-jupyterhub-gitlab-oauthenticator-7b14571d1f76) [THIS](https://nvd.nist.gov/vuln/detail/CVE-2018-7206) ISSUE WITH
 ```bash
 /opt/jupyterhub/bin/python3 -m pip install --upgrade oauthenticator
 ```

* Use main link [here](https://jupyterhub.readthedocs.io/en/stable/installation-guide-hard.html).
* Documentation [here](https://jupyterhub.readthedocs.io/en/0.7.2/index.html)[and here](https://readthedocs.org/projects/minrk-jupyterhub/downloads/pdf/latest/).
* Setting default url to home directory [here](https://github.com/jupyterhub/jupyterhub/issues/929).
* Troubleshooting [here](https://jupyterhub.readthedocs.io/en/latest/troubleshooting.html#error-after-spawning-my-single-user-server)

## Steps followed for Talon:

### Install nodejs and npm from source [here](https://nodejs.org/en/download/):
  * Unzip and tar.
  * Configure: `./configure --prefix=/cm/shared/utils/NODE/12.16.1`
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
  LDFLAGS=`pkg-config --libs-only-L libffi` ./configure --prefix=/opt/jupyterhub --with-ensurepip=install
  ```
 
### Setup Systemd service
* Used [this](https://jupyterhub.readthedocs.io/en/stable/installation-guide-hard.html#setup-systemd-service) documentaiton.
* Create folder and file:
 ```bash
 mkdir -p /opt/jupyterhub/etc/systemd
 vim /opt/jupyterhub/etc/systemd/jupyterhub.service
 ```
 * Copy the following:
 ```bash
 [Unit]
 Description=JupyterHub
 After=syslog.target network.target

 [Service]
 User=root
 Environment="PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/cm/shared/utils/NODE/12.16.1/bin/:/cm/shared/utils/GCC/6.3.0/bin:/opt/jupyterhub/bin"
 Environment="LD_LIBRARY_PATH=/cm/shared/utils/GCC/6.3.0/lib:/cm/shared/utils/GCC/6.3.0/lib64"
 ExecStart=/opt/jupyterhub/bin/jupyterhub -f /opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py & >> '/var/log/jupyterhub.log'

 [Install]
 WantedBy=multi-user.target
 ```
* Enable and start service:
 ```bash
 systemctl enable /opt/jupyterhub/etc/systemd/jupyterhub.service
 systemctl daemon-reload
 systemctl start jupyterhub.service
 systemctl status jupyterhub.service -l
 ```
* Stop and disable:
 ```bash
 systemctl stop jupyterhub.service
 systemctl status jupyterhub.service -l
 systemctl disable /opt/jupyterhub/etc/systemd/jupyterhub.service
 ```

## Overview
![https://jupyterhub.readthedocs.io/en/stable/index.html](https://jupyterhub.readthedocs.io/en/stable/_images/jhub-fluxogram.jpeg)
