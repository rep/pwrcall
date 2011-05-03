import sys
import random
import logging
logging.basicConfig(level=logging.DEBUG)

from pwrcall import loop, unloop, Node, expose, Promise
from evnet import later

class Slave(object):
	@expose
	def procfunc(self, arg):
		print 'procfunc called with array length', len(arg)
		p = Promise()
		def fulfill():
			r = sum(arg)
			print 'procfunc sending result', r
			p._resolve(r)
		later(2.0, fulfill)
		return p

n = Node(cert='cert2.pem')
s = Slave()
m = n.establish(sys.argv[1])
m.call('addslave', s)

loop()

