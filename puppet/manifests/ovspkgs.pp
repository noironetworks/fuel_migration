$role          = hiera('role')

notify {$role:}

$pkgslist = ['openvswitch-datapath-dkms', 'openvswitch-lib', 'openvswitch-common', 'openvswitch-switch']

package { 'openvswitch-datapath-dkms':
   ensure => 'latest',
} ->
package { 'openvswitch-lib':
   ensure => 'latest',
} ->
package { 'openvswitch-common':
   ensure => 'latest',
} ->
package { 'openvswitch-switch':
   ensure => 'latest',
} 
