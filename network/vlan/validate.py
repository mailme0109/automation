import vlan

def validate(validate_vlan):
	assert (validate_vlan == "found"  )," Fail"
	return ("pass")

a = vlan.check_vlan()
if (a):
    b = "found"
else:
    b = "not-found"
assert ( b == "found"  )," Fail"
        return True
