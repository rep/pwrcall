
current_evloop = None
try:
	import evnet
	current_evloop = evnet
except:
	pass
try:
	from . import gevloop
	current_evloop = gevloop
except:
	pass

def schedule(*args, **kwargs):
	return current_evloop.schedule(*args, **kwargs)
def loop(*args, **kwargs):
	return current_evloop.loop(*args, **kwargs)
def unloop(*args, **kwargs):
	return current_evloop.unloop(*args, **kwargs)
def shutdown_callback(*args, **kwargs):
	return current_evloop.shutdown_callback(*args, **kwargs)
def listenplain(*args, **kwargs):
	return current_evloop.listenplain(*args, **kwargs)

hints = []