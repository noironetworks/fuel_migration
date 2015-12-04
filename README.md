# fuel-migration
Scripts to migrate from Fuel/ML2 deployment using refrence openvswitch deployment to opflex

This repo. provides two scripts upgrade_setup.py and upgrade_node.py

upgrade_setup.py upgrades the setup from openvswitch/ML2 environment to opflex/ML2 environment.

upgrade_node.py is to be used when a node is added to the environment after the migration is complete.

Usage: upgrade_setup.py [options]

Options:
  -h, --help            show this help message and exit
  -e ENVID, --env=ENVID
                        Environment id
  -a APIC_SYSTEM_ID, --apic_system_id=APIC_SYSTEM_ID
                        new apic system id to create
  -v INFRA_VLAN, --infra_vlan=INFRA_VLAN
                        infra_vlan
  -p INFRA_IP, --infra_ip=INFRA_IP
                        infra ip
  -r VLAN_RANGE, --vlan_range=VLAN_RANGE
                        new vlan range in format physnet2:1000:1030
  -o RCFILE, --openrc=RCFILE
                        rc file with openstack credentials
  -n APIC_EXT_NET, --apic_ext_net=APIC_EXT_NET
                        Apic external net name
  -s SNAT, --snat=SNAT  SNAT gateway/mask. eg 1.2.1.1/26

All options are mandatory. (NOTE: the new vlan range should not overlap existing vlan range)

Before starting the migration, determine the correct values for the above parameters

Migration Steps:
a. Create a new repository on fuel node with debians in the tar file upgrade_debians.tar which is included

b. Update all nodes to use the new repository with highest priority.

c. Install the latest python-apicapi on controllers

d. Install neutron-ml2-driver-apic package on all nodes

e. Modify neutron config files on controllers, update the neutron database to set network_type
   to 'opflex' and segmentation_id to NULL in ml2_network_segments table.

f. Upgrade OVS on controllers

g. Stop neutron openvswitch plugin on controllers

h. Configure Opflex on controller nodes

i. Restart neutron server with 'apic_provision_infra' set to True

j. Restart neutron server with 'apic_provision_infra' set to False

k. Restart neutron dhcp agent

l. Run command 'apic neutron-sync' on controller

m. Prompt the user to add the newly created VMM domain to proper AEP and wait for response.

n. On all compute nodes, kill openvswitch plugin, upgrade OVS, configure Opflex, setup metadata files

At this point, the migration is complete, and all existing instances should have the connectivty.
The old physical domain and the old tenants can be deleted.
