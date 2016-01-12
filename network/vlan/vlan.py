from pprint import pprint
from jnpr.junos.op.vlan import VlanTable
from jnpr.junos import Device

def check_vlan():
	dev = Device(host='dc-nm-ex4200-a', user='root', password='Embe1mpls')
	dev.open()
	vlan_info = dev.cli( "show ethernet-switching interface ge-0/0/10" )
        dev.close()
	if vlan_info.find(' 1005 ') != -1:
        	return True 
	elif vlan_info.find(' 1004 ') != -1:
        	return True 
	elif vlan_info.find(' 1003 ') != -1:
        	return True 
	elif vlan_info.find(' 1002 ') != -1:
        	return True 
	elif vlan_info.find(' 1001 ') != -1:
        	return True 
        else:
		return False

