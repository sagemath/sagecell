Parts of these files were taken from or inspired by Volker Braun's scripts to build a Sage virtual appliance: https://bitbucket.org/vbraun/sage-virtual-appliance-buildscript/

# Make base centos image
vm/make-base-centos centos CentOS-6.5-x86_64-bin-DVD1.iso

# For database/logging server
vm/make-shadow-vm centos database
vm/install-database database sage-git-built.tar.gz
virsh shutdown database


# deploy out to test server
rm -rf test/centos.img test/sagecell.img
ln centos.img test/centos.img
ln sagecell.img test/sagecell.img
vm/deploy grout@localhost:/home/grout/images/test test 988 989


# deploy one test image
virsh start sagecell
virsh start database
vm/forward-port sagecell 9999 8888
vm/forward-port sagecell 3333 22

vm/forward-port deploy-database 6514 6514 # rsyslog logging; SELinux expects port 6514
vm/forward-port deploy-database 8519 8889 #permalink server
vm/forward-port deploy-database 4444 22

# sagecell server
vm/make-shadow-vm centos sagecell
vm/install-sagecell sagecell sage-git-built.tar.gz
virsh shutdown sagecell

# deploy out to production
vm/deploy grout@sage3:/home/grout/deploy server 888 889 988
vm/deploy grout@sage1:/home/grout/deploy server 888 889 988

#vm/deploy jason@combinat.math.washington.edu:/scratch/jason/sagecellvm server 888 889 session

export LIBVIRT_DEFAULT_URI='qemu:///session'
export VIRSH_DEFAULT_CONNECT_URI=$LIBVIRT_DEFAULT_URI

vm/deploy grout@sage2:/home/grout/deploy/ server 888 889
