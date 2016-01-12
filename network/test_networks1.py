# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import itertools
import time
import netaddr
import six
from vlan import vlan
from tempest_lib.common.utils import data_utils
from tempest_lib import exceptions as lib_exc
from oslo_log import log as logging
from tempest.api.network import base
from tempest.common import custom_matchers
from tempest import config
from tempest import test
import pdb
CONF = config.CONF
LOG = logging.getLogger(__name__)

class NetworksTestJSON(base.BaseNetworkTest):
    """
    Tests the following operations in the Neutron API using the REST client for
    Neutron:

        create a network for a tenant
        list tenant's networks
        show a tenant network details
        create a subnet for a tenant
        list tenant's subnets
        show a tenant subnet details
        network update
        subnet update
        delete a network also deletes its subnets
        list external networks

        All subnet tests are run once with ipv4 and once with ipv6.

    v2.0 of the Neutron API is assumed. It is also assumed that the following
    options are defined in the [network] section of etc/tempest.conf:

        tenant_network_cidr with a block of cidr's from which smaller blocks
        can be allocated for tenant ipv4 subnets

        tenant_network_v6_cidr is the equivalent for ipv6 subnets

        tenant_network_mask_bits with the mask bits to be used to partition the
        block defined by tenant_network_cidr

        tenant_network_v6_mask_bits is the equivalent for ipv6 subnets
    """

    @classmethod
    def resource_setup(cls):
        super(NetworksTestJSON, cls).resource_setup()
        cls.network = cls.create_network()
        cls.name = cls.network['name']
        cls.subnet = cls._create_subnet_with_last_subnet_block(cls.network,
                                                               cls._ip_version)
        cls.cidr = cls.subnet['cidr']
        cls._subnet_data = {6: {'gateway':
                                str(cls._get_gateway_from_tempest_conf(6)),
                                'allocation_pools':
                                cls._get_allocation_pools_from_gateway(6),
                                'dns_nameservers': ['2001:4860:4860::8844',
                                                    '2001:4860:4860::8888'],
                                'host_routes': [{'destination': '2001::/64',
                                                 'nexthop': '2003::1'}],
                                'new_host_routes': [{'destination':
                                                     '2001::/64',
                                                     'nexthop': '2005::1'}],
                                'new_dns_nameservers':
                                ['2001:4860:4860::7744',
                                 '2001:4860:4860::7888']},
                            4: {'gateway':
                                str(cls._get_gateway_from_tempest_conf(4)),
                                'allocation_pools':
                                cls._get_allocation_pools_from_gateway(4),
                                'dns_nameservers': ['8.8.4.4', '8.8.8.8'],
                                'host_routes': [{'destination': '10.20.0.0/32',
                                                 'nexthop': '10.100.1.1'}],
                                'new_host_routes': [{'destination':
                                                     '10.20.0.0/32',
                                                     'nexthop':
                                                     '10.100.1.2'}],
                                'new_dns_nameservers': ['7.8.8.8', '7.8.4.4']}}

    @classmethod
    def _create_subnet_with_last_subnet_block(cls, network, ip_version):
        """Derive last subnet CIDR block from tenant CIDR and
           create the subnet with that derived CIDR
        """
        if ip_version == 4:
            cidr = netaddr.IPNetwork(CONF.network.tenant_network_cidr)
            mask_bits = CONF.network.tenant_network_mask_bits
        elif ip_version == 6:
            cidr = netaddr.IPNetwork(CONF.network.tenant_network_v6_cidr)
            mask_bits = CONF.network.tenant_network_v6_mask_bits

        subnet_cidr = list(cidr.subnet(mask_bits))[-1]
        gateway_ip = str(netaddr.IPAddress(subnet_cidr) + 1)
        return cls.create_subnet(network, gateway=gateway_ip,
                                 cidr=subnet_cidr, mask_bits=mask_bits)

    @classmethod
    def _get_gateway_from_tempest_conf(cls, ip_version):
        """Return first subnet gateway for configured CIDR """
        if ip_version == 4:
            cidr = netaddr.IPNetwork(CONF.network.tenant_network_cidr)
            mask_bits = CONF.network.tenant_network_mask_bits
        elif ip_version == 6:
            cidr = netaddr.IPNetwork(CONF.network.tenant_network_v6_cidr)
            mask_bits = CONF.network.tenant_network_v6_mask_bits

        if mask_bits >= cidr.prefixlen:
            return netaddr.IPAddress(cidr) + 1
        else:
            for subnet in cidr.subnet(mask_bits):
                return netaddr.IPAddress(subnet) + 1

    @classmethod
    def _get_allocation_pools_from_gateway(cls, ip_version):
        """Return allocation range for subnet of given gateway"""
        gateway = cls._get_gateway_from_tempest_conf(ip_version)
        return [{'start': str(gateway + 2), 'end': str(gateway + 3)}]

    def subnet_dict(self, include_keys):
        """Return a subnet dict which has include_keys and their corresponding
           value from self._subnet_data
        """
        return dict((key, self._subnet_data[self._ip_version][key])
                    for key in include_keys)

    def _compare_resource_attrs(self, actual, expected):
        exclude_keys = set(actual).symmetric_difference(expected)
        self.assertThat(actual, custom_matchers.MatchesDictExceptForKeys(
                        expected, exclude_keys))

    def _delete_network(self, network):
        # Deleting network also deletes its subnets if exists
        self.client.delete_network(network['id'])
        if network in self.networks:
            self.networks.remove(network)
        for subnet in self.subnets:
            if subnet['network_id'] == network['id']:
                self.subnets.remove(subnet)

    def _create_verify_delete_subnet(self, cidr=None, mask_bits=None,
                                     **kwargs):
        network = self.create_network()
        net_id = network['id']
        gateway = kwargs.pop('gateway', None)
        subnet = self.create_subnet(network, gateway, cidr, mask_bits,
                                    **kwargs)
        compare_args_full = dict(gateway_ip=gateway, cidr=cidr,
                                 mask_bits=mask_bits, **kwargs)
        compare_args = dict((k, v) for k, v in six.iteritems(compare_args_full)
                            if v is not None)

        if 'dns_nameservers' in set(subnet).intersection(compare_args):
            self.assertEqual(sorted(compare_args['dns_nameservers']),
                             sorted(subnet['dns_nameservers']))
            del subnet['dns_nameservers'], compare_args['dns_nameservers']

        self._compare_resource_attrs(subnet, compare_args)
        self.client.delete_network(net_id)
        self.networks.pop()
        self.subnets.pop()
    def _try_delete_network(self, net_id):
        # delete network, if it exists
        try:
            self.client.delete_network(net_id)
        # if network is not found, this means it was deleted in the test
        except lib_exc.NotFound:
            pass
   @test.attr(type='sanity')
   @test.idempotent_id('0eee9138-0da6-4efc-a46d-578161e7b221')
    		def test_create_network(self):
        	name = data_utils.rand_name('Juniper-network')
        	network = self.create_network(network_name=name)
        	print network
        	sub = self.create_subnet(network)
        	print sub
        	time.sleep(30)
        	x = vlan.check_vlan()
        	LOG.info("Naveen x : %s"%x)
        	self.assertTrue(x==True)





class BulkNetworkOpsTestJSON(base.BaseNetworkTest):
    """
    Tests the following operations in the Neutron API using the REST client for
    Neutron:

        bulk network creation
        bulk subnet creation
        bulk port creation
        list tenant's networks

    v2.0 of the Neutron API is assumed. It is also assumed that the following
    options are defined in the [network] section of etc/tempest.conf:

        tenant_network_cidr with a block of cidr's from which smaller blocks
        can be allocated for tenant networks

        tenant_network_mask_bits with the mask bits to be used to partition the
        block defined by tenant-network_cidr
    """

    def _delete_networks(self, created_networks):
        for n in created_networks:
            self.client.delete_network(n['id'])
        # Asserting that the networks are not found in the list after deletion
        body = self.client.list_networks()
        networks_list = [network['id'] for network in body['networks']]
        for n in created_networks:
            self.assertNotIn(n['id'], networks_list)

    def _delete_subnets(self, created_subnets):
        for n in created_subnets:
            self.client.delete_subnet(n['id'])
        # Asserting that the subnets are not found in the list after deletion
        body = self.client.list_subnets()
        subnets_list = [subnet['id'] for subnet in body['subnets']]
        for n in created_subnets:
            self.assertNotIn(n['id'], subnets_list)

    def _delete_ports(self, created_ports):
        for n in created_ports:
            self.client.delete_port(n['id'])
        # Asserting that the ports are not found in the list after deletion
        body = self.client.list_ports()
        ports_list = [port['id'] for port in body['ports']]
        for n in created_ports:
            self.assertNotIn(n['id'], ports_list)

class BulkNetworkOpsIpV6TestJSON(BulkNetworkOpsTestJSON):
    _ip_version = 6


class NetworksIpV6TestJSON(NetworksTestJSON):
    _ip_version = 6

class NetworksIpV6TestAttrs(NetworksIpV6TestJSON):

    @classmethod
    def skip_checks(cls):
        super(NetworksIpV6TestAttrs, cls).skip_checks()
        if not CONF.network_feature_enabled.ipv6_subnet_attributes:
            raise cls.skipException("IPv6 extended attributes for "
                                    "subnets not available")

#    @test.attr(type='sanity')
#    @test.idempotent_id('0eee9138-0da6-4efc-a46d-578161e7b221')
#    def test_create_network(self):
#        name = data_utils.rand_name('Juniper-network')
#        network = self.create_network(network_name=name)
#        print network
#        sub = self.create_subnet(network)
#        print sub
#        time.sleep(30)
#	#x = vlan.check_vlan()
#        #LOG.info("Naveen x : %s"%x)
#        #self.assertTrue(x==True)
#    
#    @test.attr(type='sanity1')
#    @test.idempotent_id('0eee9138-0da6-4efc-a46d-578161e7b222')
#    def test_delete_network(self):
#	   self.delete_network('Juniper-network')
#           x= vlan.check_vlan()
#	   self.assertTrue(x==True)
#        #name = data_utils.rand_name('Juniper-network')
#        #network = self.create_network(network_name=name)
#        #print network
#        #sub = self.create_subnet(network)
#        #print sub
#        #time.sleep(60)
#	#x = vlan.check_vlan()
#        #LOG.info("Naveen x : %s"%x)
#        #self.assertTrue(x==True)
