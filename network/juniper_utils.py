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
