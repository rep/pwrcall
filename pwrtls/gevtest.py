
import sys
import os
import argparse
import traceback
import struct
import random

import gevent.server
import gevent.socket
import bson
import nacl

BUFSIZE = 16384

# state_file is BSON encoded dict/hash
# with pub,priv keys for the keypair
# and nonce for securing the longtermkey encryption on new connections
# {'pub':'\x\x\x', 'priv':'\x\x\x', 'nonce':'\x\x\x'}
def load_state_file(path):
	if not os.path.exists(path): return False
	d = open(path, 'rb').read()
	if not bson.is_valid(d): return False
	return bson.BSON(d).decode()

def init_state(path):
	pub, priv = nacl.crypto_box_keypair()
	nonce = rand48()
	state = {
		'pub':_b(pub), 
		'priv':_b(priv), 
		'nonce':nonce,
	}
	d = bson.BSON.encode(state)
	open(path, 'wb').write(d)
	return d

def _b(x): return bson.binary.Binary(x)

# message creation helpers
def rand48(): return random.randint(2**47, 2**48-1)

def lnonce(num): return 'pwrnonce' + struct.pack('QQ', num, rand48())

def snonce(num): return 'pwrnonceshortXXX' + struct.pack('Q', num)

class pwrtls_exception(Exception): pass
class pwrtls_closed(Exception): pass

# get args from enced bson dict
def from_bson(enced, *args):
	dec = bson.BSON(enced).decode()
	if len(args) == 1: return dec[args[0]]
	return [dec[i] for i in args]


class pwrtls(object):
	def __init__(self, state, rpub=None):
		self.state = state
		self.rpub = rpub
		print 'my pubkey:', self.state['pub'].encode('hex')

	def handle_server(self, sock, addr):
		try: pwrtls_server(sock, addr, self).handle()
		except: traceback.print_exc()
		finally: sock.close()

	def handle_client(self, sock, addr):
		if not self.rpub:
			print 'We need the remote long-term public key for clients!'
			sock.close()
			return

		try: pwrtls_client(sock, addr, self).handle()
		except: traceback.print_exc()
		finally: sock.close()


class pwrtls_connection(object):
	def __init__(self, sock, addr, ptls):
		self.sock = sock
		self.addr = addr
		self.ptls = ptls

	def recv_frame(self):
		lengthbytes = self.sock.recv(4)
		if not lengthbytes: raise pwrtls_closed('Connection closed.')

		framelen = struct.unpack('I', lengthbytes)[0]
		buf = ''
		while len(buf) < framelen:
			tmp = self.sock.recv(BUFSIZE)
			if not tmp: raise pwrtls_closed('Connection closed.')
			buf += tmp
		return buf

	def send_frame(self, data):
		data = struct.pack('I', len(data)) + data
		self.sock.sendall(data)

	def handle(self):
		self.shortpub, self.shortpriv = nacl.crypto_box_keypair()
		self.initialize()
		
		while True:
			t = self.recv_frame()
			print 'recv:', repr(t)

		sock.close()

	def initialize(self):
		raise Exception("Implement in subclass!")

	def message(self, data):
		m = { 'box': _b(nacl.crypto_box(data, snonce(self.nonce), self.rspub, self.shortpriv)), 'n': self.nonce }
		self.nonce += 2
		return bson.BSON.encode(m)


class pwrtls_client(pwrtls_connection):
	def initialize(self):
		self.nonce = 5
		print 'client!'

		self.send_frame(self.clienthello())

		# receive server hello with his short-term pubkey
		data = self.recv_frame()
		box = from_bson(data, 'box')
		self.remote_shortpub = nacl.crypto_box_open(box, snonce(2), self.ptls.rpub, self.shortpriv)

		# send verification message authenticating our short-term key with our long-term one
		self.send_frame(self.clientverify())

		self.send_frame('hi from client!')

	def clienthello(self):
		m = { 'spub': _b(self.shortpub), 'box': _b(nacl.crypto_box('pwrzero0'*8, snonce(1), self.ptls.rpub, self.shortpriv)) }
		return bson.BSON.encode(m)

	def clientverify(self):
		self.ptls.state['nonce'] += 1

		vn = lnonce(self.ptls.state['nonce'])
		verifybox = _b(nacl.crypto_box(
			str(_b(self.shortpub)), vn, self.ptls.rpub, self.ptls.state['priv']
		))

		m = { 'box': _b(nacl.crypto_box(
			str(bson.BSON.encode({
				'lpub': _b(self.ptls.state['pub']),
				'v': verifybox,
				'vn': _b(vn),
			})),
			snonce(3), self.remote_shortpub, self.shortpriv
		))}
		return bson.BSON.encode(m)


class pwrtls_server(pwrtls_connection):
	def initialize(self):
		print 'server!'

		# first frame is client_hello, with his short-term pubkey
		data = self.recv_frame()
		box, self.remote_shortpub = from_bson(data, 'box', 'spub')
		opened = nacl.crypto_box_open(box, snonce(1), self.remote_shortpub, self.ptls.state['priv'])
		if not 'pwrzero0' in opened: raise pwrtls_exception("hello box failure.")

		# now send our hello message with short-term pubkey
		self.send_frame(self.serverhello())

		# receive verification message for authenticating the short-term key
		data = self.recv_frame()
		box = from_bson(data, 'box')
		opened = nacl.crypto_box_open(box, snonce(3), self.remote_shortpub, self.shortpriv)
		remote_longpub, vbox, vnonce = from_bson(opened, 'lpub', 'v', 'vn')

		# we can only open this if we actually have the clients long-term key.
		if self.ptls.rpub:
			if str(remote_longpub) != self.ptls.rpub: raise pwrtls_exception('remote long-term key mismatch.')
			boxshort = nacl.crypto_box_open(vbox, vnonce, self.ptls.rpub, self.ptls.state['priv'])
			if str(boxshort) != str(self.remote_shortpub): raise pwrtls_exception('remote short-term key verify failed.')

		self.send_frame('hi from server!')

	def serverhello(self):
		m = { 'box': _b(nacl.crypto_box(self.shortpub, snonce(2), self.remote_shortpub, self.ptls.state['priv'])) }
		return bson.BSON.encode(m)

def main():
	parser = argparse.ArgumentParser(description='pwrcall nacl test.')

	parser.add_argument('action', help='connect/listen', choices=['connect', 'listen', 'c', 'l'])
	parser.add_argument('--state', dest='state', help='path to state file', default='pwr.state')
	parser.add_argument('--sock', dest='sock', help='where to connect / what to bind', required=True)
	parser.add_argument('--rpub', dest='rpub', help='remove public key for verification')

	args = parser.parse_args()

	state = load_state_file(args.state)
	if not state:
		print 'invalid state file. generating new one...'
		state = init_state(args.state)

	if args.rpub: args.rpub = args.rpub.decode('hex')

	ptls = pwrtls(state, args.rpub)

	if args.action[0] == 'c':
		ip, port = args.sock.split(':', 1)
		port = int(port)

		socket = gevent.socket.create_connection((ip, port))
		ptls.handle_client(socket, (ip, port))

	elif args.action[0] == 'l':
		if ':' in args.sock: ip, port = args.sock.split(':', 1)
		else: ip, port = '0.0.0.0', args.sock
		port = int(port)
		
		server = gevent.server.StreamServer((ip, port), ptls.handle_server)
		server.serve_forever()

	return 0

if __name__ == '__main__':
	sys.exit(main())
