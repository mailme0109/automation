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
from juniper_utils import *
import pdb
CONF = config.CONF
LOG = logging.getLogger(__name__)

class JuniperNetworkTests(base.BaseNetworkTest):

    @test.idempotent_id('0eee9138-0da6-4efc-a46d-578161e7b221')
    def test_create_network(self):
        name = data_utils.rand_name('Juniper-network')
        network = self.create_network(network_name=name)
        print network
	gateway = '20.20.20.1'
	cidr = netaddr.IPNetwork('20.20.20.0/24')
	ip_version = 4
        sub = self.create_subnet(network,gateway=gateway,cidr=cidr,ip_version=ip_version)
        #print sub
        time.sleep(60)
	x = vlan.check_vlan()
        LOG.info("Naveen x : %s"%x)
        self.assertTrue(x==True)
	self.resource_cleanup()
	x = vlan.check_vlan()
        LOG.info("Naveen x : %s"%x)
        self.assertTrue(x!=True)
        #self.assertTrue(True==True)
