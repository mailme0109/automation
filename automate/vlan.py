from pprint import pprint
from jnpr.junos.op.vlan import VlanTable
from jnpr.junos import Device
import pdb

def check_vlan();
	dev = Device(host='bng-dcnb1-qfx3500-a.englab.juniper.net', user='root', password='Embe1mpls')
	dev.open()
	vlan_info = dev.cli( "show ethernet-switching interface ge-0/0/16" )
	if vlan_info.find('test') != -1:
    	print "found vlan"
    	return true;
       # dev.close()
