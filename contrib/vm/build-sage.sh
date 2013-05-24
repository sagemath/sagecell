#!/bin/sh

VM=sagecell
./start $VM

# vmm is:
# Host vmm
#    User root
#    HostName localhost
#    Port 5457
#    NoHostAuthenticationForLocalhost yes


VMSSH=vmm
### The Sage version
SOURCE=$1
if [ -z $SOURCE ] || [ ! -f $SOURCE ] ; then
    echo "Cannot find Sage source archive $SOURCE."
    exit 1
fi

echo 'Syncing sage source'
rsync --progress -avv -e ssh $SOURCE $VMSSH:/home/sage-source.tar

#scp "$SCRIPTSDIR"/systemd-run-sage.service $VMSSH:/lib/systemd/system/sage@.service

#scp "$SCRIPTSDIR"/sage-bash-profile $VMSSH:/home/sage/.bash_profile

ssh $VMSSH -T <<EOF | tee  install.log
  set -v
  echo 'Updating system'
  yum -y update
  yum clean all

  #echo 'Setting up systemd scripts'
  #cd /etc/systemd/system/getty.target.wants
  #ln -sf /lib/systemd/system/sage@.service getty@tty8.service

  echo 'Resetting accounts'
  /usr/sbin/userdel -r sageserver
  /usr/sbin/userdel -r sageworker
  if grep sagecell /etc/group; then
    /usr/sbin/groupdel sagecell
  fi
  /usr/sbin/groupadd sagecell
  /usr/sbin/useradd sageserver --groups sagecell
  /usr/sbin/useradd sageworker --groups sagecell

  echo 'Setting up ssh keys'
  su -l sageserver -c 'ssh-keygen -q -N "" -f /home/sageserver/.ssh/id_rsa'
  su -l sageworker -c 'mkdir .ssh && chmod 700 .ssh'
  cp -r /home/sageserver/.ssh/id_rsa.pub /home/sageworker/.ssh/authorized_keys
  chown -R sageworker.sageworker /home/sageworker/
  restorecon -R /home/sageserver/.ssh
  restorecon -R /home/sageworker/.ssh

  echo 'Making permanent mount'
  mkdir /permanent
  if ! grep -q "permanent" /etc/fstab; then
     echo /dev/vdb /permanent ext4 defaults,noexec 1 2 >> /etc/fstab
  fi
  mount -a

  echo 'Setting quotas'
  setquota -u sageworker 1000000 1200000 20000 30000 /

  echo 'Making temporary directory'
  su -l sageserver
  mkdir /tmp/sagecell
  chown sageserver.sagecell /tmp/sagecell
  chmod g=wxs,o= /tmp/sagecell

  echo 'Extracting sage'
  su -l sageserver
  #set -v
  tar xf /home/sage-source.tar
  rm sage
  ln -s sage* sage
  cd sage

  echo 'Compiling Sage'
  # export SAGE_ATLAS_ARCH=fast
  export SAGE_ATLAS_LIB=/usr/lib64/atlas/
  #export SAGE_FAT_BINARY="yes"
  export MAKE='make -j16'
  make
  #make test
  ./sage <<EOFSAGE
     quit
EOFSAGE

  echo 'Installing sagecell'
  rm -rf local/lib/python/site-packages/[iI]Python*
  ./sage -sh -c "easy_install https://github.com/ipython/ipython/archive/0d4706f.zip"
  ./sage -i http://sage.math.washington.edu/home/jason/sagecell-spkg/sagecell-2013-05-20.spkg

EOF

scp config.py $VMSSH:/home/sageserver/sage/devel/sagecell/config.py

RC=`grep "Error building Sage" install.log` 
if [ "$RC" != "" ]; then
   echo "Error building Sage!"
   #VBoxManage unregistervm $UUID --delete
   exit 1
fi

ssh $VMSSH -T <<EOF
  # make sure the config file is owned by the right person
  chown sageserver.sageserver /home/sageserver/sage/devel/sagecell/config.py

  # very bad: disable firewall and change permissions
  chmod o+rx /home/sageserver
  iptables -I INPUT 1 -p tcp --dport 8888 -j ACCEPT # open up incoming web connections to sage cell server
  iptables -I INPUT 1 -i lo -j ACCEPT # open up loopback for all traffic
  /sbin/service iptables save
EOF

ssh $VMSSH -t -t <<EOF
  # get the localhost in the known_hosts file
  su -l sageserver -c 'ssh -q -oStrictHostKeyChecking=no sageworker@localhost echo hi'
  echo 'done'
  exit
EOF

# don't shut down; just exit
exit

ssh $VMSSH -T <<EOF
  #dd if=/dev/zero of=/zerofile ; rm -f /zerofile
  #shutdown -h now
EOF


echo "Waiting for the guest addition installation to finish..."
STATUS=`virsh dominfo $VM | grep 'State:.*running'`
while [ "$STATUS" != "" ]; do
    date
    sleep 10
    STATUS=`virsh dominfo $VM | grep 'State:.*running'`
done
#if [ $? -ne 0 ]; then
#   echo "Failed to wait for installation to finish!"
#   exit 1
#fi
