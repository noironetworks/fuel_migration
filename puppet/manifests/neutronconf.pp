$role          = hiera('role')
$apicsystemid  = hiera('apic_system_id')
$mysql_hash    = hiera('mysql_hash', {})

$mysql_passwd = $mysql_hash['root_password']

$new_vlan_range = hiera('new_vlan_range')

$snat_gateway = hiera('snat_gateway')
$apic_ext_net = hiera('apic_ext_net')

notify {$role:}
notify {$mysql_passwd:}

neutron_plugin_ml2 {
   'ml2/type_drivers':                     value => 'opflex,local,flat,vlan,gre,vxlan';
   'ml2/tenant_network_types':             value => 'opflex';
   'ml2/mechanism_drivers':                value => 'cisco_apic_ml2';
   'ml2_type_vlan/network_vlan_ranges':    value => $new_vlan_range;
}

neutron_plugin_ml2_cisco {
   'DEFAULT/apic_system_id':                                 value => $apicsystemid;
   'opflex/networks':                                        value => "*";
   'ml2_cisco_apic/enable_aci_routing':                      value => 'True';
   'ml2_cisco_apic/enable_optimized_dhcp':                   value => 'True';
   'ml2_cisco_apic/enable_optimized_metadata':               value => 'True';
    "apic_external_network:${apic_ext_net}/host_pool_cidr":  value => $snat_gateway;
}

case $role {
     /controller/: {
         exec {'update_database':
            command => "/usr/bin/mysql -u root -p$mysql_passwd neutron -e \"update ml2_network_segments set network_type='opflex' \" ";
         }
         exec {'update_database2':
            command => "/usr/bin/mysql -u root -p$mysql_passwd neutron -e \"update ml2_network_segments set segmentation_id=NULL \" ";
         }
     }
}
