# PFSENSE-API
This may seem like yet another attempt to provide API like access to PfSense, a platform that has failed to provide even rudimentary API access.  The current iteration is a READ-ONLY API.  This is intended to provide running statistics and health information, not configuration updates.  At a future date I may provide some write access functionality.

## Usage Examples

    from pfsense_api import PfsenseApi
  
    \# connect and login
    pfsense = PfsenseApi(host='192.168.1.1', port=8443, username='admin', password='admin', verify_ssl=True, ca_cert_path='ca_file.pem')

    \# get all system info
    system_stats = pfsense.system_stats()

    \# get specific API data
    general = pfsense.call_api('general')
    software_system = pfsense.call_api('software_system')
    thermal = pfsense.call_api('thermal')
    disks = pfsense.call_api('disks')
    interface_stats = pfsense.call_api('interface_stats')
    openvpn_connections = pfsense.call_api('openvpn_connections')
    dhcp_leases = pfsense.call_api('dhcp_leases')
    gateways = pfsense.call_api('gateways')
    routes_v4 = pfsense.call_api('routes_v4')
    routes_v6 = pfsense.call_api('routes_v6')
    carp = pfsense.call_api('carp')
    arp = pfsense.call_api('arp')
    ndp = pfsense.call_api('ndp')
    states = pfsense.call_api('states')
    haproxy = pfsense.call_api('haproxy')

## Supported API's

Since PfSense does not provide any API interfaces, these API's are based on parsing HTML tables, JSON (in a couple of instance) or text strings.

All data returned (except for those that are already in JSON format) are returned as named tuples to make accessing the data easier.  For example:

    general = pfsense.call_api('general')
    print(eneral.memory_used_percent)
    print(uptime_days)

### General

Most values are self explanitory.  The uptime values are collective.  i.e. x days + x hours + x minutes + x seconds (this is a straight string parse).  MBUF is memory buffers used for packet routing.  CPU tick information is used to generate the % CPU usage information.

- cpu_tick_total
- cpu_tick_used
- memory_used_percent
- uptime_days
- uptime_hours
- uptime_minutes
- uptime_seconds
- state_used
- state_max
- temp_c
- datetime
- cpu_freq_current
- cpu_freq_max
- sys_load_1
- sys_load_5
- sys_load_15
- mbuf_current
- mbuf_max
- mbuf_percent
- state_percent

### Software_system

Software system returns the currently installed version, the latest available version, and a 'comparison' of the two.

- installed_version
- version
- pkg_version_compare

### Thermal

This API will return the output of any available thermal sensors on the system.

### Disks

This API will return a list of the local disks on the system with the following:

- mount
- size (in bytes)
- used (in bytes)
- usage
  - fs_type (i.e. ufs / tmpfs)
  - usage_percent

### Interface_stats

The interface stats will return a list of the interfaces with the interface level counters:

- bytes_in
- bytes_out
- collisions
- errors_in
- errors_out
- packets_in
- packets_out

### OpenVPN Connections

This API will return a list of OpenVPN servers and their associated active connections.  This also includes OpenVPN sessions initiated from the PfSense firewall to another server.

- bytes_received
- bytes_sent
- last_change
- local_address
- name
- remote_host
- service
- status
- virtual_address

### dhcp_leases

This API returns 3 tables from the DHCP status page

#### Pool Status

- failover_group
- my_state
- peer_state
- since (for my state)
- since_1 (for peer state)

#### Leases

- description
- end
- hostname
- ip_address
- mac_address

#### Lease Utilization

- capacity
- interface
- pool_end
- pool_start
- used
- utilization

### gateways

This will return a list of the gateways on the system as well as the monitoring status of the gateway.

- description
- gateway
- loss
- monitor
- name
- trr
- trrsd
- status

### routes_v4 / routes_v6

This will return the IPv4 / IPv6 routes active on the system.

- net
- gw
- flags
- uses
- mtu
- interface

### carp

This will pull the status of CARP virtual addresses on the system.

- description
- interface_and_vhid
- status
- virtual_ip_address

### arp

This will pull a list of all ARP entries on the system.

- hostname
- interface
- ip_address
- link_type
- mac_address
- status

### ndp

This will pull a list of the IPv6 neighbor discovery table on the system.

- expiration
- hostname
- interface
- ipv6_address
- mac_address

### states

This will return a list of all the states present on the system.

NOTE:  This is subject to change.  Currently it is only parsing the text on the table and may be updated to parse the fields further.

### haproxy

This will return the data pulled from the HA proxy service.

NOTE:  This works, however the returend data is difficult to interpret.  I do not have a description for each of the fields at this time.

## Class

Class: PfsenseApi

    A class designed to handle login and data querying from a PfSense firewall.

    Attributes:

        host: PfSense host address.
        port: PfSense port (default is 443).
        supported_read_apis: List of READ API's supported by this release
        verify_ssl: Boolean flag to verify SSL certificates (default is True).
        log_level: Logging level (default is INFO).
        ca_cert_path: Path to CA certificate file (default is None).

    Methods:

    __init__(self, host, username, password, port=443, log_level=INFO, verify_ssl=True, ca_cert_path=None)
        Initializes a PfsenseApi instance, establishes a session, and logs in.
    
    login(self, username, password) -> bool
        Logs into the PfSense firewall using the provided username and password.

    system_stats(self) -> dict
        Collects system stats and general info from the firewall using supported APIs and returns the data as a dictionary.

    def call_api(self, api_name:str) -> list|dict
        Call a specific API and return the data

    get_response(self, method='get', path='/index.php', data=None, headers=None, parameters=None, retry=RETRY, timeout=TIMEOUT) -> requests.Response
        Executes an HTTP request with optional parameters, data, and headers.
