import sys
import random
import logging
logging.basicConfig(level=logging.DEBUG)

from pwrcall import loop, unloop, Node, expose, Promise
from evnet import later

class Processround(object):
	def __init__(self, slaves, data, funcname, combinefunc):
		self.slaves = slaves
		self.data = data
		self.funcname = funcname
		self.combinefunc = combinefunc
		self.p = Promise()
		self.results = []

	def run(self):
		amount = len(self.data) / len(self.slaves)
		for i in range(len(self.slaves)):
			rp = self.slaves[i].call(self.funcname, self.data[i*amount:(i*amount)+amount])
			rp._when(self.resultcb)
			rp._except(self.exceptcb)

		return self.p

	def exceptcb(self, e):
		self.p._smash(e)

	def resultcb(self, result):
		self.results.append(result)
		if len(self.results) == len(self.slaves):
			self.p._resolve(self.combinefunc(self.results))
	

class Master(object):
	def __init__(self):
		self.n = Node(cert='serverside.pem')
		self.n.listen(port=10000)
		ref = self.n.register(self, 'master')
		print 'Master at', self.n.refurl(ref)

		self.slaves = {}
		later(5.0, self.process)

	def process(self):
		slaves = self.slaves.values()
		if not slaves:
			later(5.0, self.process)
			print 'process, but no slaves'
			return

		somerand = random.randint(10,200)
		data = range(somerand * 720, (somerand+1) * 720)

		pr = Processround(slaves, data, 'procfunc', sum)
		p = pr.run()
		p._except(self.roundfailed)
		p._when(self.roundresult, sum(data))

	def roundresult(self, r, should):
		print 'roundresult, shouldbe:', r, should, r==should
		later(5.0, self.process)

	def roundfailed(self, e):
		print 'processround failed:', e
		later(5.0, self.process)

	@expose
	def addslave(self, slave, conn):
		self.slaves[conn] = slave

		def connclosed(reason):
			sl = self.slaves.pop(conn, None)
			print 'slave {0} gone, as conn {1} is closed.'. format(sl, conn)
		
		conn._on('close', connclosed)
		return True

m = Master()

loop()

