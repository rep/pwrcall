
from pwrcall import expose

class Math(object):
	@expose
	def add(self, a, b):
		return a+b
	@expose
	def mul(self, a, b):
		return a*b

pwrobj = Math()

