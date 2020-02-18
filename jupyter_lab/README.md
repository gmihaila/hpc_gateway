# Jupyter Lab Python Server


## User side debugging
* Check '.jupyter_lab.log' log file in jupyter running directory.

## Test Server:
`$ flask run -h 0.0.0.0 --with-threads`

## [Deploy Flask App](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xvii-deployment-on-linux)

* Install gunicorn to use as production server.
  * To launch it:
  `$ gunicorn -b localhost:8000 -w 4 jupyter_lab:app`

* Setup Supervisor [NOT SET YET]

* Setup nginx server:
  * Install nginx:
  ```
  $ sudo apt-get update
  $ sudo apt-get install nginx -y
  $ sudo /etc/init.d/nginx stop
  $ sudo rm /etc/nginx/sites-enabled/default
  $ cd /etc/nginx/sites-enabled/
  $ vim jupyter_lab
  ```
  Make sure to set `ssl off;`
