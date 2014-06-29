Some files were taken from or inspired by Volker Braun's scripts to build a Sage virtual appliance:
https://bitbucket.org/vbraun/sage-virtual-appliance-buildscript/

# Make base centos image
vm/make-base-centos centos CentOS-6.5-x86_64-bin-DVD1.iso

# sagecell server
vm/make-shadow-vm centos sagecell
vm/install-sagecell sagecell

# deploy out to test server
vm/deploy-test user@server:directory

# deploy out to production after SSH-ing to user@server:directory
vm/deploy-production



# For database/logging server
vm/make-shadow-vm centos database
vm/install-database database sage-git-built.tar.gz
virsh shutdown database

virsh start database
vm/forward-port deploy-database 6514 6514 # rsyslog logging; SELinux expects port 6514
vm/forward-port deploy-database 8519 8889 #permalink server
vm/forward-port deploy-database 4444 22


