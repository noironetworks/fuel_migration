$role          = hiera('role')
$oid           = hiera('apic_system_id')
notify {$oid:}

case $role {
     /controller/: {

             $pkgslist = ['python-apicapi', 'neutron-ml2-driver-apic']

             package { $pkgslist:
                ensure => 'latest',
             }
    
     }
     'compute': {

             $pkgslist = ['neutron-ml2-driver-apic']

             package { $pkgslist:
                ensure => 'latest',
             }
    
     }

}
