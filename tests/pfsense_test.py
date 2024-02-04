import unittest
from logging_handler import create_logger, DEBUG
import json
import os
from pfsense_api import PfsenseApi

logger = create_logger(DEBUG, name='PfSense testing')

class pfsense_tests(unittest.TestCase):
    def test_1_login(self):
        logger.debug(f"{'='*20} Running test {self._testMethodName}: {self._testMethodDoc}")
        test_file = os.path.join('local', 'tests', 'test_config.json')
        with open(test_file, 'r', encoding='utf-8') as input_file:
            pfsense_config = json.load(input_file)
        pfsense = PfsenseApi(**pfsense_config)
        stats = pfsense.all_system_stats()
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
        self.assertTrue(isinstance(stats, dict))

if __name__== '__main__':
    unittest.main()