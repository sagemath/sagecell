#!/bin/sh

### The Sage version
SOURCE=$1
if [ -z $SOURCE ] || [ ! -f $SOURCE ] ; then
    echo "Cannot find Sage source archive $SOURCE."
    exit 1
fi

# Start and install virtualbox guest additions
STATUS=`virsh dominfo centos-vm | grep 'State:.*running'`
if [ $? -ne 0 ]; then
    virsh start centos-vm
    if [ $? -ne 0 ]; then
       echo "Failed to start virtual machine!"
       exit 1
    fi
    STATUS="booting"
    echo "Booting virtual machine"
fi
sleep 2
virsh qemu-monitor-command centos-vm --hmp 'hostfwd_add ::5456-:22'
STATUS=`ssh -oNoHostAuthenticationForLocalhost=yes -p5456 root@localhost echo "ready"`
while [ "$STATUS" != "ready" ]; do
    echo "Waiting for VM to start."
    sleep 10
    STATUS=`ssh -oNoHostAuthenticationForLocalhost=yes -p5456 root@localhost echo "ready"`
done

set -v
scp -oNoHostAuthenticationForLocalhost=yes -P5456 \
    $SOURCE root@localhost:/home/sagecell/sage-source.tar

#scp -oNoHostAuthenticationForLocalhost=yes -P5456 \
#    "$SCRIPTSDIR"/systemd-run-sage.service root@localhost:/lib/systemd/system/sage@.service

#scp -oNoHostAuthenticationForLocalhost=yes -P5456 \
#    "$SCRIPTSDIR"/sage-bash-profile root@localhost:/home/sage/.bash_profile

ssh -oNoHostAuthenticationForLocalhost=yes -p5456 root@localhost -T <<EOF | tee  install.log
  set -v

  yum -y update
  yum clean all

  #cd /etc/systemd/system/getty.target.wants
  #ln -sf /lib/systemd/system/sage@.service getty@tty8.service
  chown -R sagecell.sagecell /home/sagecell/

  su -l sagecell
  set -v
  cd
  tar xf sage-source.tar
  rm -f sage-source.tar
  rm sage
  ln -s sage* sage
  cd sage
  # export SAGE_ATLAS_ARCH=fast
  export SAGE_ATLAS_LIB=/usr/lib64/atlas/
  #export SAGE_FAT_BINARY="yes"
  export MAKE='make -j16'
  make
  #make test
  ./sage <<EOFSAGE
     quit
EOFSAGE
  # install sagecell
  rm -rf sage/local/lib/python/site-packages/[iI]Python*
  ./sage -sh -c "easy_install https://github.com/ipython/ipython/archive/0d4706f.zip"
  ./sage -i http://sage.math.washington.edu/home/jason/sagecell-spkg/sagecell-2013-05-20.spkg
EOF

RC=`grep "Error building Sage" install.log` 
if [ "$RC" != "" ]; then
   echo "Error building Sage!"
   #VBoxManage unregistervm $UUID --delete
   exit 1
fi

sleep 5
ssh -oNoHostAuthenticationForLocalhost=yes -p5456 root@localhost -T <<EOF
  #dd if=/dev/zero of=/zerofile ; rm -f /zerofile
  shutdown -h now
EOF

echo "Waiting for the guest addition installation to finish..."
STATUS=`virsh dominfo centos-vm | grep 'State:.*running'`
while [ "$STATUS" != "" ]; do
    date
    sleep 10
    STATUS=`virsh dominfo centos-vm | grep 'State:.*running'`
done
#if [ $? -ne 0 ]; then
#   echo "Failed to wait for installation to finish!"
#   exit 1
#fi
