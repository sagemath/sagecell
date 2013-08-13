Parts of these files were taken from or inspired by Volker Braun's scripts to build a Sage virtual appliance: https://bitbucket.org/vbraun/sage-virtual-appliance-buildscript/


vm/make-base-centos centos mnt
vm/make-shadow-vm centos sagecell
vm/install-sagecell sagecell sage-5.11.rc1-built.tar
virsh shutdown sagecell

vm/deploy server jason@combinat.math.washington.edu /scratch/jason/sagecellvm 888 889
vm/deploy server grout@localhost /home/grout/images/deploy 888 889


rm -rf test/centos.img test/sagecell.img
ln centos.img test/centos.img
ln sagecell.img test/sagecell.img
vm/deploy test grout@localhost /home/grout/images/test 988 989
