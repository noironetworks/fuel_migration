$debug                         = hiera('debug', true)
$auth_region                   = 'RegionOne'
$admin_tenant_name             = 'services'
$neutron_admin_username        = 'neutron' 
$neutron_config                = hiera('quantum_settings')
$neutron_user_password         = $neutron_config['keystone']['admin_password']
$service_endpoint              = hiera('management_vip')
$neutron_metadata_proxy_secret = $neutron_config['metadata']['metadata_proxy_shared_secret']

class {'neutron::compute_neutron_metadata':
    debug          => $debug,
    auth_region    => $auth_region,
    auth_url       => "http://${service_endpoint}:35357/v2.0",
    auth_user      => $neutron_admin_username,
    auth_tenant    => $admin_tenant_name,
    auth_password  => $neutron_user_password, 
    shared_secret  => $neutron_metadata_proxy_secret,
    metadata_ip    => $service_endpoint,
}
