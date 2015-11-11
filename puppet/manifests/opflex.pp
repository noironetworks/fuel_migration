$network_scheme     = hiera('network_scheme', {})
prepare_network_config($network_scheme)
$intf   = get_network_role_property('neutron/private', 'phys_dev')
$opflex_interface   = $intf[0]

$br_intf_hash = br_intf_hash()

$br_to_patch = $br_intf_hash[$opflex_interface][bridge]

$opflex_encap_type = 'vlan'    
$apic_system_id  = hiera('apic_system_id')
$apic_infra_vlan = hiera('apic_infra_vlan')
$apic_infra_ip = hiera('apic_infra_ip')

class {'opflex::opflex_agent':
        opflex_ovs_bridge_name             => 'br-int',
        opflex_uplink_iface                => $opflex_interface,
        opflex_uplink_vlan                 => $apic_infra_vlan,
        opflex_apic_domain_name            => $apic_system_id,
        opflex_encap_type                  => $opflex_encap_type,
        opflex_peer_ip                     => $apic_infra_ip,
        opflex_remote_ip                   => '',
        br_to_patch                        => $br_to_patch,
}

