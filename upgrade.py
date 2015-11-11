#!/usr/bin/env python

import optparse, json, os, sys, netifaces
from fabric.api import env, run, local, hide, cd, lcd, put
from fabric.contrib.files import exists as fab_exists
import pdb

def query_continue_abort(question, default="no"):
    valid = {"continue": True, "abort": False}
    prompt = "[continue/abort]"

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'continue' or 'abort' \n")

class Fnode(object):
    def __init__(self, jel):
	self.hostname = jel['fqdn']
	self.cluster = jel['cluster']
	self.roles = [str(x).strip() for x in jel['roles'].split(',')]
	if 'compute' in self.roles:
	    self.role = 'compute'
	if 'controller' in self.roles:
	    self.role = 'controller'

	self.id = jel['id']
	self.repolist = None

    def _runcmd(self, cmd, hide_output=True):
	env.host_string = self.hostname
	env.user = 'root'
	if hide_output:
	    with hide('output'):
		op = run(cmd)
	else:
	    op = run(cmd)
	return op

    def buildRepolist(self):
	cmd = "grep -H ^deb /etc/apt/sources.list /etc/apt/sources.list.d/*"
	op = self._runcmd(cmd)
	self.repolist = op.split("\r\n")

    def addhieradata(self, asid, infra_vlan, infra_ip, vlan_range):
	cmd = "echo apic_system_id: %s >> /etc/hiera/nodes.yaml" % asid
	self._runcmd(cmd)
	cmd = "echo apic_infra_vlan: %s >> /etc/hiera/nodes.yaml" % infra_vlan
	self._runcmd(cmd)
	cmd = "echo apic_infra_ip: %s >> /etc/hiera/nodes.yaml" % infra_ip
	self._runcmd(cmd)
	cmd = "echo new_vlan_range: %s >> /etc/hiera/nodes.yaml" % vlan_range
	self._runcmd(cmd)

    def removehieradata(self):
	cmd = "sed -i '/^apic_system_id/d' /etc/hiera/nodes.yaml"
	self._runcmd(cmd)
	cmd = "sed -i '/^apic_infra_vlan/d' /etc/hiera/nodes.yaml"
	self._runcmd(cmd)
	cmd = "sed -i '/^apic_infra_ip/d' /etc/hiera/nodes.yaml"
	self._runcmd(cmd)
	cmd = "sed -i '/^new_vlan_range/d' /etc/hiera/nodes.yaml"
	self._runcmd(cmd)

    def addRepo(self, reponame, repouri):
	cmd = "echo %s > /etc/apt/sources.list.d/%s.list" % (repouri, reponame)
	self._runcmd(cmd)

	#cmd = "echo -e \"Package: * \n Pin: release o=Cisco,v=1.0,l=upgrade_repository \n Pin-Priority: 1500\n\" > /etc/apt/preferences.d/upgrade_repository.pref" 
	cmd = "cat > /etc/apt/preferences.d/upgrade_repository.pref <<EOL \nPackage: * \nPin: release o=Cisco,v=1.0,l=upgrade_repository \nPin-Priority: 1500\nEOL"
	self._runcmd(cmd)

	self._runcmd("apt-get update")

    def removeRepo(self, rstr):
	""" Hide the repo which has regex rstr in its url """
	if not self.repolist:
	    self.buildRepolist()

	for repo in self.repolist:
	    sfile, dummy, repostr = repo.partition(':')
	    if rstr in repostr:
		destfile = os.path.join(os.path.dirname(sfile), "."+os.path.basename(sfile))
		cmd = "/bin/mv %s %s" % (sfile, destfile)
		self._runcmd(cmd)
	self._runcmd("apt-get update")

    def copydir(self, sdir, dest):
	self._runcmd("mkdir -p %s" % dest)
	env.host_string = self.hostname
	env.user = 'root'
	put(sdir, dest)

    def _puppetrun(self, manifest):
	env.host_string = self.hostname
	env.user = 'root'
	with cd('/root/upgrade'):
	    run("puppet apply --modulepath=puppet/modules puppet/manifests/%s" % manifest)

    def basepkgs(self):
	self._puppetrun('basepkgs.pp')

    def ovspkgs(self):
	self._puppetrun('ovspkgs.pp')

    def opflex(self):
	self._puppetrun('opflex.pp')

    def neutronconfig(self):
	self._puppetrun('neutronconf.pp')

    def infratrue(self):
	self._puppetrun('infratrue.pp')
      
    def infrafalse(self):
	self._puppetrun('infrafalse.pp')
      
    def restart_neutron(self):
	self._runcmd("service neutron-server restart")

    def restart_neutron_dhcp(self):
	self._runcmd("service neutron-dhcp-agent restart")

    def nuke_neutron_openvswitch(self):
	if self.role == "controller":
	    self._runcmd("crm resource stop clone_p_neutron-plugin-openvswitch-agent")

	if self.role == "compute":
	    self._runcmd("service neutron-plugin-openvswitch-agent stop")
	    self._runcmd("echo manual > /etc/init/neutron-plugin-openvswitch-agent.override")

def instantiate_nodes(envid):
    fnodelist = []
    cmd = "fuel --json --env-id %s node" % envid
    jstr = local(cmd, capture=True)
    jlist = json.loads(jstr)

    for jel in jlist:
	nobj = Fnode(jel)
	fnodelist.append(nobj)

    return fnodelist

def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-e", "--env", help="Environment id", dest='envid')
    parser.add_option("-a", "--apic_system_id", help="new apic system id to create", dest='apic_system_id')
    parser.add_option("-v", "--infra_vlan", help="infra_vlan", dest='infra_vlan')
    parser.add_option("-p", "--infra_ip", help="infra ip", dest='infra_ip')
    parser.add_option("-r", "--vlan_range", help="new vlan range in format physnet2:1000:1030", dest='vlan_range')
    parser.add_option("-o", "--openrc", help="rc file with openstack credentials", dest='rcfile')
    (options, args) = parser.parse_args()

    if not options.envid:
	print "Please provide the environment id"
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


    fnodelist = instantiate_nodes(options.envid)
    f_controller_nodes = []
    f_compute_nodes = []
    for n in fnodelist:
	if n.role == "controller":
	    f_controller_nodes.append(n)
	if n.role == "compute":
	    f_compute_nodes.append(n)
	  

#    for n in fnodelist:
#	n.buildRepolist()
#	n.removeRepo('cisco')

    cnode = f_controller_nodes[0]
    env.host_string = cnode.hostname
    env.user = 'root'
    if fab_exists(options.rcfile):
	pass
    else:
	print "File %s does not exist on %s" % (options.rcfile, env.host_string)
	sys.exit(-1)

    #setup the new repo from tar file, expect the tar file to be in the same dir as this script
    try:
	os.makedirs('/var/www/nailgun/upgrade_repository')
    except:
	pass
    tfile = os.path.join(sys.path[0], "upgrade_debians.tar")
    cmd = "tar -xf %s -C /var/www/nailgun/upgrade_repository" % tfile
    local(cmd)
    with lcd('/var/www/nailgun/upgrade_repository'):
	local("dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz")

    uri = "deb http://%s:8080/upgrade_repository /" % (netifaces.ifaddresses('eth0')[2][0]['addr'])
    for n in fnodelist:
	n.addRepo(reponame='upgrade', repouri=uri)


    #copy puppet manifests, templates to nodes
    sdir = os.path.join(sys.path[0], 'puppet')
    print sdir
    for n in fnodelist:
	n.copydir(sdir=sdir, dest="/root/upgrade")

    #upgrade non-disruptive packages on all nodes
    for n in fnodelist:
	n.addhieradata(options.apic_system_id, options.infra_vlan, options.infra_ip, options.vlan_range)
	n.basepkgs()

    #update neutron configuration files, modify database
    for n in fnodelist:
	n.neutronconfig()

    #install ovs packages
    for n in f_controller_nodes:
	n.ovspkgs()

    for n in f_controller_nodes:
	n.nuke_neutron_openvswitch()

    #opflex on controllers
    for n in f_controller_nodes:
	n.opflex()

    fcontroller = f_controller_nodes[0]
    fcontroller.infratrue()
    fcontroller.restart_neutron()
    fcontroller.infrafalse()

    for n in f_controller_nodes:
	n.restart_neutron()
	n.restart_neutron_dhcp()

    try:
    	cnode = f_controller_nodes[0]
        env.host_string = cnode.hostname
        env.user = 'root'
        cmd = "source %s; apic neutron-sync" % options.rcfile
	with hide('output'):
	    run(cmd)
    except:
	pass

    r = query_continue_abort('At this time please add new VMM domain to proper AEP ')
    if r:
	pass
    else:
	sys.exit(-1)
       

    for n in f_compute_nodes:
	n.nuke_neutron_openvswitch()

    #opflex on computes
    for n in f_compute_nodes:
	n.ovspkgs()
	n.opflex()


    #remove the update repo and enable the old repo

    for n in fnodelist:
	n.removehieradata()
if __name__ == "__main__":
    main()


