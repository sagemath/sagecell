#!/bin/sh

### The Sage version
VERSION=5.10.beta4


SOURCE="src/sage-$VERSION.tar"
if [ ! -f $SOURCE ] ; then
    echo "Cannot find Sage source archive $SOURCE in the $SRCDIR directory."
    exit 1
fi
export SOURCE


# Start and install virtualbox guest additions
virsh start centos-vm
if [ $? -ne 0 ]; then
   echo "Failed to start virtual machine!"
   exit 1
fi
STATUS="booting"
sleep 2
virsh qemu-monitor-command centos-vm --hmp 'hostfwd_add ::5456-:22'
while [ "$STATUS" != "ready" ]; do
    echo "Waiting for VM to start."
    sleep 10
    STATUS=`ssh -oNoHostAuthenticationForLocalhost=yes -p5456 root@localhost echo "ready"`
done


scp -oNoHostAuthenticationForLocalhost=yes -P5456 \
    "$SRCDIR/sage-$VERSION.tar" root@localhost:/home/sage/sage-source.tar

#scp -oNoHostAuthenticationForLocalhost=yes -P5456 \
#    "$SCRIPTSDIR"/systemd-run-sage.service root@localhost:/lib/systemd/system/sage@.service

#scp -oNoHostAuthenticationForLocalhost=yes -P5456 \
#    "$SCRIPTSDIR"/sage-bash-profile root@localhost:/home/sage/.bash_profile

ssh -oNoHostAuthenticationForLocalhost=yes -p5456 root@localhost -T <<EOF | tee  install.log
  set -v
  #cd /etc/systemd/system/getty.target.wants
  #ln -sf /lib/systemd/system/sage@.service getty@tty8.service
  chown -R sagecell.sagecell /home/sagecell/

  su sagecell
  set -v
  cd
  tar xf sage-source.tar
  rm -f sage-source.tar
  ln -s sage* sage
  cd sage
  # export SAGE_ATLAS_ARCH=fast
  export SAGE_ATLAS_LIB=/usr/lib64/atlas
  #export SAGE_FAT_BINARY="yes"
  export MAKE='make -j12'
  make
  #make test
EOF

RC=`grep "Error building Sage" "install.log` 
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
STATUS="State:           running"
while [ "$STATUS" != "" ]; do
    STATUS=`virsh dominfo centos-vm | grep 'State:.*running'`
    date
    sleep 20
done
if [ $? -ne 0 ]; then
   echo "Failed to wait for installation to finish!"
   exit 1
fi
