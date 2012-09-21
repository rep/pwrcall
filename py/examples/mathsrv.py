import sys
import logging
logging.basicConfig(level=logging.DEBUG)

from pwrcall import loop, unloop, Node, expose

class Math(object):
	@expose
	def add(self, a, b):
		return a+b

n = Node(cert='serverside.pem')
m = Math()
if len(sys.argv) > 1:
	ref = n.register(m, cap=sys.argv[1])
else:
	ref = n.register(m)
n.listen(port=10000)
print 'math obj ready at', n.refurl(ref)

loop()

