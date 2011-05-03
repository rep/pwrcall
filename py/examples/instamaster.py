import sys
import logging
logging.basicConfig(level=logging.DEBUG)

from pwrcall import loop, unloop, Node, expose
from pwrcall.util import NodeException, parse_url

class Instamaster(object):
	def __init__(self):
		self.clients = {}

	@expose
	def open(self, pwrurl, filename, conn):
		try:
			fp, hints, cap = parse_url(pwrurl)
		except:
			raise NodeException('Error in pwrcall URL.')

		cli = self.clients.get(fp, None)
		if not cli: raise NodeException('Target client unavailable.')
		return cli.call(cap, 'open', filename)

	def on_new_conn(self, rc, addr):
		rc.onready()._when(self.register_conn)

	def register_conn(self, rc):
		cli = self.clients.get(rc.conn.peerfp, None)
		if cli:
			logging.warn('New conn {0} kicking old {1}.'.format(rc.conn.peerfp, cli.conn.peerfp))
			cli.close()

		self.clients[rc.conn.peerfp] = rc
		def connclosed(reason):
			self.clients.pop(rc.conn.peerfp, None)
			
		rc._on('close', connclosed)

def main():
	n = Node(cert='serverside.pem')
	im = Instamaster()
	ref = n.register_object(im, 'im')
	n._on('connection', im.on_new_conn)
	n.listen(port=20001)
	print 'Instamaster at', n.refurl(ref)

	loop()

	return 0

if __name__ == '__main__':
	sys.exit(main())

