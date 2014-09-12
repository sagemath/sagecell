# Advanced Installation

Here we describe how to setup a "production" instance of SageCell server.

## Create the "Enveloping Virtual Machine" (EVM).

This is optional, if you are willing to dedicate a physical machine to SageCell, but it is assumed in scripts and instructions.

1.  Configure a package proxy, e.g. Apt-Cacher NG, for the machine that will host EVM.
2.  Install KVM and configure it for your account, consult your OS documentation as necessary.
3.  Download `build_host.sh` and `preseed.host` to some directory, that will be used also for the login script and SSH keys.

    ```bash
    mkdir ~/scevm
    cd ~/scevm
    wget https://raw.githubusercontent.com/sagemath/sagecell/master/contrib/vm/build_host.sh
    wget https://raw.githubusercontent.com/sagemath/sagecell/master/contrib/vm/preseed.host
    chmod a+x build_host.sh
    ```

4.  Make adjustments to `build_host.sh`, in particular the proxy and EVM resources.
5.  Make adjustments to `preseed.host` if desired, e.g. change time zone and locale settings.
6.  Run `build_host.sh` and wait: the installation make take half an hour or even longer with a slow Internet connection. Your terminal settings may get messed up in the process since we do not suppress the installation console, it will not happen after installation.

    ```bash
    ./build_host.sh
    ```

    (If your virt-install does not understand `OSVARIANT=ubuntutrusty`, you may try a different version of Ubuntu here, while keeping the same `LOCATION`. Using a different base OS is probably possible, but is likely to require some further changes to build commands.)

7.  You should get `ssh_host.sh` script that allows you to SSH as root to EVM. If it does not work, you probably need to adjust the IP address in it manually. Note that root password is disabled, you must use the SSH key generated during installation.

    ```bash
    ./ssh_host.sh
    ```

## Inside of EVM

1.  Download `container_manager.py` and make it executable (or run it with python3).

    ```bash
    wget https://raw.githubusercontent.com/sagemath/sagecell/master/contrib/vm/container_manager.py
    chmod a+x container_manager.py
    ```

2.  Adjust it if necessary. In particular, note that the default permalink server is the public SageCell server.
3.  Run it. If all goes well, the base OS and the master SageCell container will be created. Expect it to take at least an hour.

    ```bash
    ./container_manager.py | tee first_run.log
    ```

4.  To create several compute nodes behind a load balancer, run

    ```bash
    ./container_manager.py --deploy
    ```

## Outside of EVM

1.  Configure HTTP and/or HTTPS access to EVM:80. HTTPS has to be decrypted before EVM, but it is recommended to avoid certain connection problems. Examples of HA-Proxy and Apache configurations will soon be provided.
2.  Configure (restricted) access to EVM:8888 for testing newer versions of SageCell.
3.  Configure (restricted) access to EVM:9999 for HA-Proxy statistics page.
4.  If you are going to run multiple EVMs, consider adjusting `/etc/rsyslog.d/sagecell.conf` in them to collect all logs on a single server.

## Maintenance Notes

1.  Used GitHub repositories are cached in EVM to reduce download size for upgrades.
2.  EVM is configured to install security updates automatically.
3.  Base and master containers are always fully updated before cloning deployment nodes.
4.  Deployment nodes are configured to install security updates automatically.
5.  EVM, deployment, and test containers should start automatically after reboot of the host machine.
6.  If you want to upgrade to the current SageCell, run

    ```bash
    ./container_manager.py -m --deploy
    ```

    Note that after the new version is started, the script will wait for a couple hours to make sure that users in the middle of interacting with the old one have finished their work.
7. If you want to first test the new version while keeping the old one in production, run instead

    ```bash
    ./container_manager.py -m -t
    ```

    and once you are satisfied with it
    
    ```bash
    ./container_manager.py --deploy
    ```

8.  If you would like to customize your SageCell, make changes in the master container before deployment.

**If these instructions are unclear or do not work, please let us know!**
