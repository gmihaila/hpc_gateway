# HPC Gateway

</br>

## [JupyterHub](https://github.com/gmihaila/hpc_gateway/tree/master/jupyterhub)
* Currently running on `vis-04.acs.unt.edu`.
* Currently running on `vis.acs.unt.edu`.
* Dev running on `vis-03.acs.unt.edu`.

</br>

## [Open OnDemand](https://github.com/gmihaila/hpc_gateway/tree/master/ood)
* Currently installing & testing on `vis-04.acs.unt.edu`.

</br>

## [Jupyter Lab Python Server](https://github.com/gmihaila/hpc_gateway/tree/master/jupyter_lab) [Not Supported Anymore]
* Tested.
* Will stop using - not reliable.
* Automate process of ssh tunneling and port forwarding from HPC cluster to a publicly available VM.
* Configure jupyter notebook configuraiton files.
* Enforce jupyter notebook password useage.
* Enforces timeout jupyter notebook session [can be customizable].
* Generates random available ports to forward the HPC session.

### To view Database [Sqlite-Web](https://github.com/coleifer/sqlite-web):

`$ sqlite_web -H 0.0.0.0 database_jupyter_lab.db`
Browse:
`http://jupyterlab.hpc.unt.edu:8080/`

</br>

## Web integrated development environment (IDE)
* not started yet

</br>

## AutoML Web Interface
* not started yet

</br>

All code is indented using: `autopep8 -i *.py`.

