$role          = hiera('role')

notify {$role:}

case $role {
     /controller/: {

             $pkgslist = ['openvswitch-datapath-dkms', 'openvswitch-lib', 'openvswitch-common', 'openvswitch-switch']

             package { $pkgslist:
                ensure => 'latest',
             }
    
     }
     'compute': {

             $pkgslist = ['openvswitch-datapath-dkms', 'openvswitch-lib', 'openvswitch-common', 'openvswitch-switch']

             package { $pkgslist:
                ensure => 'latest',
             }
    
     }

}
