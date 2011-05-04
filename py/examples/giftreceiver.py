import logging
logging.basicConfig(level=logging.DEBUG)

from pwrcall import loop, unloop, Node, expose, Promise
from evnet import later

n = Node(cert='serverside2.pem')

class Giftreceiver(object):
	def __init__(self):
		self.donaterunpromise = Promise()
		self.obj = None

	@expose
	def donate(self, url):
		#print obj, obj.conn, obj.functions
		print url
		self.obj = n.establish(url)
		r = self.obj.call('add', 10, 31)
		r._when(self.done)
		return self.donaterunpromise

	def done(self, r):
		print 'done using the object, result:', r
		self.donaterunpromise._resolve('Thanks, i am done!.')
		later(3, self.retry)

	def works(self, r):
		print 'reusing worked, result:', r
		later(3, self.retry)

	def err(self, e):
		print 'reusing error, e:', e

	def retry(self):
		if self.obj:
			r = self.obj.call('add', 40, 31)
			r._when(self.works)
			r._except(self.err)
			

ref = n.register(Giftreceiver(), cap='giftreceive')
n.listen(port=10001)
print 'giftreceiver ready at', n.refurl(ref)

loop()

