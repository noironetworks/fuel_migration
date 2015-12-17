#!/usr/bin/env python

from upgradelib import *

def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-e", "--env", help="Environment id", dest='envid')
    parser.add_option("-i", "--nodeid", help="Node id", dest="nodeid")
    parser.add_option("-a", "--apic_system_id", help="new apic system id to create", dest='apic_system_id')
    parser.add_option("-v", "--infra_vlan", help="infra_vlan", dest='infra_vlan')
    parser.add_option("-p", "--infra_ip", help="infra ip", dest='infra_ip')
    parser.add_option("-r", "--vlan_range", help="new vlan range in format physnet2:1000:1030", dest='vlan_range')
    parser.add_option("-o", "--openrc", help="rc file with openstack credentials", dest='rcfile')
    parser.add_option("-n", "--apic_ext_net", help="Apic external net name", dest='apic_ext_net')
    parser.add_option("-s", "--snat", help="SNAT gateway/mask. eg 1.2.1.1/26", dest='snat')
    parser.add_option("-x", "--ext_subnet", help="External network router subnet name", dest='ext_subnet')
    parser.add_option("-y", "--ext_subnet_gateway", help="External network router subnet gateway", dest='ext_subnet_gw')
    parser.add_option("-z", "--ext_subnet_cidr", help="External network router subner cidr", dest='ext_subnet_cidr')
    parser.add_option("-t", "--ext_subnet_range", help="Ext. net. subnet allocation pool range, eg 1.109.1.2:1.109.1.100", dest='ext_subnet_ap_range')

    (options, args) = parser.parse_args()

    if not options.envid:
	print "Please provide the environment id"
	sys.exit(-1)

    if not options.nodeid:
        print "Please provide the node id to upgrade"
        sys.exit(-1)

    if not options.apic_system_id:
	print "Please provide the apic_system_id"
	sys.exit(-1)

    if not options.infra_vlan:
	print "Please provide the infra vlan"
	sys.exit(-1)

    if not options.infra_ip:
	print "Please provide the infra ip"
	sys.exit(-1)

    if not options.vlan_range:
	print "Please provide the new vlan range"
	sys.exit(-1)

    if not options.rcfile:
	print "Please provide openstack credentials file"
	sys.exit(-1)

    if not options.apic_ext_net:
	print "Please provide the APIC external network"
	sys.exit(-1)

    if not options.snat:
	print "Please provide the SNAT gateway/maskbits"
	sys.exit(-1)

    if not options.ext_subnet:
        print "Please provide the external net subnet name"
        sys.exit(-1)

    if not options.ext_subnet_gw:
        print "Please provide the external net subnet gateway"
        sys.exit(-1)

    if not options.ext_subnet_cidr:
        print "Please provide the external net subnet cidr"
        sys.exit(-1)

    if not options.ext_subnet_ap_range:
        print "Please provide the allocation pool range for external net subnet"
        sys.exit(-1)

    if not len(options.ext_subnet_ap_range.split(':')) == 2:
        print "Invalid format for allocation pool eg. 1.109.1.10:1.109.1.100"
        sys.exit(-1)
    ap_start,ap_end = options.ext_subnet_ap_range.split(':')

    if not len(options.vlan_range.split(':')) == 3:
        print "Invalid format for vlan range. eg physnet2:2001:2030"
        sys.exit(-1)

    if not re.match('^(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[1-9]|[1-9][1-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\/([1-9]|[1-2]\d|3[0-2])$', options.snat):
	print "Invalid SNAT gateway/maskbits. Eg. 1.2.1.1/24"
	sys.exit(-1)


    fnodelist = instantiate_nodes(options.envid)
    f_controller_nodes = []
    f_compute_nodes = []
    for n in fnodelist:
	if n.role == "controller":
	    f_controller_nodes.append(n)
	if n.role == "compute":
	    f_compute_nodes.append(n)

    node_to_upgrade = None
    for n in f_compute_nodes:
	if n.id == int(options.nodeid):
	    node_to_upgrade = n
	    break

    if not node_to_upgrade:
	print "Node id %s is not part of environment id %s in compute role" % (options.nodeid, options.envid)
	sys.exit(-1)

    cnode = f_controller_nodes[0]
    if exists_remote(cnode.hostname, options.rcfile):
	pass
    else:
	print "File %s does not exist on %s" % (options.rcfile, cnode.hostname)
	sys.exit(-1)


    #setup the new repo from tar file, expect the tar file to be in the same dir as this script
    try:
	os.makedirs('/var/www/nailgun/upgrade_repository')
    except:
	pass
    tfile = os.path.join(sys.path[0], "upgrade_debians.tar")
    cmd = "tar -xf %s -C /var/www/nailgun/upgrade_repository" % tfile
    _cmd = shlex.split(cmd)
    p = subprocess.Popen(_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    os.system("cd /var/www/nailgun/upgrade_repository; dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz")

    uri = "deb http://%s:8080/upgrade_repository /" % (netifaces.ifaddresses('eth0')[2][0]['addr'])
    node_to_upgrade.addRepo(reponame='upgrade', repouri=uri)

    #copy puppet manifests, templates to nodes
    sdir = os.path.join(sys.path[0], 'puppet')
    node_to_upgrade.copydir(sdir=sdir, dest="/root/upgrade")

    node_to_upgrade.addhieradata(options.apic_system_id, options.infra_vlan, options.infra_ip, options.vlan_range, options.apic_ext_net, options.snat, options.ext_subnet,options.ext_subnet_gw,options.ext_subnet_cidr,ap_start,ap_end)
    node_to_upgrade.basepkgs()

    #update neutron configuration files, modify database
    node_to_upgrade.neutronconfig()

    node_to_upgrade.nuke_neutron_openvswitch()

    node_to_upgrade.compute_metadata_agent()
    node_to_upgrade.ovspkgs()
    node_to_upgrade.opflex()
    node_to_upgrade.compute_neutron_server()

    node_to_upgrade.removehieradata()

if __name__ == "__main__":
    main()


