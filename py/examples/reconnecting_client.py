#!/usr/bin/python

import sys

from pwrcall import Node
from evnet import later, loop

CERT = None
PURL = 'pwrcall://9cb608c8aeb7e0c517a293026299d944439e626d@127.0.0.1:3000/NmZlODM0M2ZmYTc1Zjg1ZjYxZGIxNWI0NGJhN2ZhMmY='

class ClientClass(object):
	def __init__(self):
		self.n = Node(cert=CERT)
		self.rpcconn = None
		self.connect()
		
	def connect(self, reason=''):
		#self.rc = self.n.connect(HOST, PORT)
		conn_promise = self.n.establish(PURL)
		conn_promise._when(self.established)
		conn_promise._except(self.notestablished)

	def established(self, rpcconn):
		def delay(reason): later(3.0, self.connect)
		rpcconn.conn._on('close', delay)

		print 'now we are connected!', rpcconn
		self.rpcconn = rpcconn

	def notestablished(self, error):
		later(3.0, self.connect)

def main():
	cli = ClientClass()
	loop()
	return 0

if __name__ == '__main__':
	sys.exit(main())
