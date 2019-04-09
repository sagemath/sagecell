#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o xtrace

APTPROXY="http://your-proxy-here-or-delete-proxy-from-preseed/"
MAC=52:54:00:5a:9e:c1   # Must start with 52:54:00

VM_NAME=schostvm
OSVARIANT=ubuntu18.04
LOCATION="http://archive.ubuntu.com/ubuntu/dists/bionic/main/installer-amd64/"

sed "s|APTPROXY|$APTPROXY|" preseed.host > preseed.cfg

if ! [ -f ${VM_NAME}_rsa ]; then
    ssh-keygen -q -N "" -C "sc_admin" -f ${VM_NAME}_rsa
fi
SSHKEY=`cat ${VM_NAME}_rsa.pub`
sed -i "s|SSHKEY|$SSHKEY|" preseed.cfg

virt-install \
--connect qemu:///system \
--name $VM_NAME \
--description "Host for SageCell instances." \
--ram=32768 \
--cpu host \
--vcpus=12 \
--location $LOCATION \
--initrd-inject=preseed.cfg \
--extra-args="console=ttyS0" \
--os-type=linux \
--os-variant=$OSVARIANT \
--disk pool=default,size=100,device=disk,bus=virtio,format=qcow2,cache=writeback \
--network network=default,model=virtio,mac=$MAC \
--graphics none \
--autostart \
--check-cpu \
--noreboot \

# For a dedicated partition use
#--disk path=/dev/???,bus=virtio \
    
# Make a script to SSH inside, assuming that IP will not change
virsh --connect qemu:///system start $VM_NAME
sleep 30
IP=`ip n|grep $MAC|grep -Eo "^[0-9.]{7,15}"`
cat <<EOF > ssh_host.sh
#!/usr/bin/env bash

if [[ \`virsh --connect qemu:///system domstate $VM_NAME\` != "running" ]]; then
    if ! virsh --connect qemu:///system start $VM_NAME; then
       echo "Failed to start $VM_NAME"
       exit 1
    fi
    sleep 30
fi

ssh -i ${VM_NAME}_rsa root@$IP
EOF
chmod u+x ssh_host.sh
# Power cycle VM, otherwise bash completion does not work for LXC.
virsh --connect qemu:///system shutdown $VM_NAME
