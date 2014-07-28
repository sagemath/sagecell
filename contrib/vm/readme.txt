Some files were taken from or inspired by Volker Braun's scripts to build a Sage virtual appliance:
https://bitbucket.org/vbraun/sage-virtual-appliance-buildscript/

# Create a directory for building images and go there.
mkdir sc_build
cd sc_build
# Get clone_repositories, make it executable, and run it.
wget https://github.com/sagemath/sagecell/raw/master/contrib/vm/clone_repositories
chmod u+x clone_repositories
./clone_repositories
# Copy vm from sagecell to the build one.
cp -r github/sagecell/contrib/vm .
# Generate sagecell_rsa key to be used for machine access.
ssh-keygen -q -t rsa -N "" -f sagecell_rsa
#
# Adjust public key in the end of vm/base-centos.kickstart-template
#
# Get OS image: we are at the moment using
# CentOS-6.5-x86_64-bin-DVD1.iso
# which just got outdated. The plan is to migrate to another base soon.
#
# Create a file rootpassword with encrypted root password
# (see make-base-centos for the format)

# Make base VM image.
vm/make-base-centos centos CentOS-6.5-x86_64-bin-DVD1.iso

# Make base sagecell VM.
vm/make-shadow-vm centos sagecell
vm/install-sagecell sagecell

# Deploy out to test server.
vm/deploy-test user@server:directory

# Deploy out to production after SSH-ing to user@server:directory
vm/deploy-production



# For database/logging server
vm/make-shadow-vm centos database
vm/install-database database sage-git-built.tar.gz
virsh shutdown database

virsh start database
vm/forward-port deploy-database 6514 6514 # rsyslog logging; SELinux expects port 6514
vm/forward-port deploy-database 8519 8889 #permalink server
vm/forward-port deploy-database 4444 22

