
def ioprotos():
	return ','.join(serializers)

def addio(name):
	serializers.append(name)

def gen_banner():
	return 'pwrcall {0} - caps: {1}\n'.format(version, ioprotos())

# for this to work, ioprotos must be given in the same order on every node
def choose_ioproto(remote_info):
	if not 'caps:' in remote_info: return None

	caps = remote_info[remote_info.find('caps:')+5:].strip()
	for i in serializers:
		if i in caps: return i
	
	# no common serializer?
	return None

serializers = []
version = '0.3'

