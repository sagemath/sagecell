Parts of these files were taken from or inspired by Volker Braun's scripts to build a Sage virtual appliance: https://bitbucket.org/vbraun/sage-virtual-appliance-buildscript/


vm/make-base-centos centos mnt
vm/make-shadow-vm centos sagecell
vm/install-sagecell sagecell sage-5.9-built.tar
virsh shutdown sagecell

vm/deploy server jason@combinat.math.washington.edu /fastscratch/jason/sagecellvm 888 889
vm/deploy server grout@localhost /home/grout/images/deploy 888 889

