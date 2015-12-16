import optparse, json, os, sys, netifaces, pipes, shlex, re, logging
import pdb
import subprocess

logger = logging.getLogger('master')
hdlr = logging.FileHandler(os.path.join(sys.path[0], 'master_log'))
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

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

def exists_remote(host, path):
    proc = subprocess.Popen(['ssh', host, 'test -f %s' % pipes.quote(path)])
    proc.wait()
    return proc.returncode == 0

def local_cmd(cmd, cwd=None):
    print "Executing: %s" % cmd
    a1 = shlex.split(str(cmd))
    logger.debug(a1)
    if cwd:
       p = subprocess.Popen(a1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    else:
       p = subprocess.Popen(a1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = p.communicate()
    logger.debug(o)
    logger.debug(e)

class Fnode(object):
    def __init__(self, jel):
	self.hostname = jel['fqdn']
	self.cluster = jel['cluster']
	self.roles = [str(x).strip() for x in jel['roles'].split(',')]
	if 'compute' in self.roles:
	    self.role = 'compute'
	elif 'controller' in self.roles:
	    self.role = 'controller'
        else:
            self.role = 'ignore'

	self.id = jel['id']
	self.repolist = None

    def _runcmd(self, cmd, cwd=None):
        c1 = "ssh %s" % self.hostname + " " + cmd
        print "Executing: %s" % c1
        a1 = shlex.split(str(c1))
        logger.debug(a1)
        if cwd:
           p = subprocess.Popen(a1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        else:
           p = subprocess.Popen(a1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        o, e = p.communicate()
        logger.debug(o)

    def buildRepolist(self):
	cmd = "grep -H ^deb /etc/apt/sources.list /etc/apt/sources.list.d/*"
	op = self._runcmd(cmd)
	self.repolist = op.split("\r\n")

    def addhieradata(self, asid, infra_vlan, infra_ip, vlan_range, apic_ext_net, snat):
	cmd = "echo apic_system_id: %s >> /etc/hiera/nodes.yaml" % asid
	self._runcmd(cmd)
	cmd = "echo apic_infra_vlan: %s >> /etc/hiera/nodes.yaml" % infra_vlan
	self._runcmd(cmd)
	cmd = "echo apic_infra_ip: %s >> /etc/hiera/nodes.yaml" % infra_ip
	self._runcmd(cmd)
	cmd = "echo new_vlan_range: %s >> /etc/hiera/nodes.yaml" % vlan_range
	self._runcmd(cmd)
	cmd = "echo apic_ext_net: %s >> /etc/hiera/nodes.yaml" % apic_ext_net
	self._runcmd(cmd)
	cmd = "echo snat_gateway: %s >> /etc/hiera/nodes.yaml" % snat
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
	cmd = "sed -i '/^apic_ext_net/d' /etc/hiera/nodes.yaml"
	self._runcmd(cmd)
	cmd = "sed -i '/^snat_gateway/d' /etc/hiera/nodes.yaml"
	self._runcmd(cmd)

    def addRepo(self, reponame, repouri):
	cmd = "echo %s > /etc/apt/sources.list.d/%s.list" % (repouri, reponame)
	self._runcmd(cmd)

	#cmd = "echo -e \"Package: * \n Pin: release o=Cisco,v=1.0,l=upgrade_repository \n Pin-Priority: 1500\n\" > /etc/apt/preferences.d/upgrade_repository.pref" 
	#cmd = "cat > /etc/apt/preferences.d/upgrade_repository.pref <<EOL \nPackage: * \nPin: release o=Cisco,v=1.0,l=upgrade_repository \nPin-Priority: 1500\nEOL"
	#self._runcmd(cmd)

        srcfile = os.path.join(sys.path[0], 'upgrade_repository.pref')
        destfile = "/etc/apt/preferences.d/upgrade_repository.pref"
        cmd = "scp %s %s:%s" % (srcfile, self.hostname, destfile)
        local_cmd(cmd)

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
        cmd = "scp -rp %s %s:%s" % (sdir, self.hostname, dest)
        local_cmd(cmd)

    def _puppetrun(self, manifest):
	cmd = "puppet apply --debug --logdest /var/log/puppet.log --modulepath=/root/upgrade/puppet/modules /root/upgrade/puppet/manifests/%s" % manifest
	self._runcmd(cmd)

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
      
    def compute_metadata_agent(self):
        self._puppetrun("compute_metadata_agent.pp")

    def compute_neutron_server(self):
        self._puppetrun("compute_neutron_server.pp")

    def restart_neutron(self):
	self._runcmd("service neutron-server restart")

    def restart_neutron_dhcp(self):
	self._runcmd("service neutron-dhcp-agent restart")

    def nuke_neutron_openvswitch(self):
	if self.role == "controller":
            self._runcmd("/usr/sbin/pcs constraint colocation remove clone_p_neutron-plugin-openvswitch-agent clone_p_neutron-dhcp_agent")
            self._runcmd("/usr/sbin/pcs constraint order remove clone_p_neutron-plugin-openvswitch-agent clone_p_neutron-dhcp_agent")
	    self._runcmd("crm resource stop clone_p_neutron-plugin-openvswitch-agent")

	if self.role == "compute":
	    self._runcmd("service neutron-plugin-openvswitch-agent stop")
	    self._runcmd("echo manual > /etc/init/neutron-plugin-openvswitch-agent.override")

def instantiate_nodes(envid):
    fnodelist = []
    cmd = "fuel --json --env-id %s node" % envid
    #jstr = local(cmd, capture=True)
    jstr = subprocess.Popen(["fuel", "--json", "--env-id" , envid, "node"], stdout=subprocess.PIPE).communicate()[0]
    jlist = json.loads(jstr)

    for jel in jlist:
	nobj = Fnode(jel)
        if not nobj.role == "ignore":
           fnodelist.append(nobj)

    return fnodelist

