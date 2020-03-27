# Open OnDemand - Talon

</br>

## Install
* [Install Software From RPM](https://osc.github.io/ood-documentation/master/installation/install-software.html#install-software-from-rpm)
* Skip [Modify System Security](https://osc.github.io/ood-documentation/master/installation/modify-system-security.html#modify-system-security)
* Start OOD: [Start Apache Server](https://osc.github.io/ood-documentation/master/installation/start-apache.html#start-apache)
  #### Change port from `80` to `8090`:
  * Change the `httpd.conf` from `/opt/rh/httpd24/root/etc/httpd/conf/httpd.conf` to `listen 8090`:
    ```bash
    vim /opt/rh/httpd24/root/etc/httpd/conf/httpd.conf

    listen 8090
    ```
  * Change the `ood-portal.conf` from `/opt/rh/httpd24/root/etc/httpd/conf.d/ood-portal.conf` to `virtual host 8090`:
    ```bash
    vim /opt/rh/httpd24/root/etc/httpd/conf.d/ood-portal.conf

    virtual host 8090
    ```
    
* [TO DO] [Add SSL Suport](https://osc.github.io/ood-documentation/master/installation/add-ssl.html#add-ssl-support)
* [Add LDAP Suport](https://osc.github.io/ood-documentation/master/installation/add-ldap.html#add-ldap-support) was changed to use PAM using [ood-auth-be-handled-by-pam](https://discourse.osc.edu/t/can-ood-auth-be-handled-by-pam/81)
* [TO DO] Configure [Authentication](https://osc.github.io/ood-documentation/master/authentication.html#authentication)
* [Add Cluster Configuration](https://osc.github.io/ood-documentation/master/installation/add-cluster-config.html#add-cluster-configuration-files) using `/talon.yml` and setting in path: `/etc/ood/config/clusters.d/talon.yml`

  
