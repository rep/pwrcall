
import os
import logging
import socket
import weakref
import inspect
import itertools
import time
import collections
import traceback

from . import util
from . import evloop
from . import serialize
from . import info
from .promise import Promise
from .util import NodeException, expose, Referenced, EventGen

RPC_REQUEST = 0
RPC_RESPONSE = 1
RPC_NOTIFY = 2

class nodeFunctions(object):
	"""pwrcall node functionality"""
	def __init__(self, node):
		self.node = node

	@expose
	def get(self, cap):
		"""Retrieve objects registered with the Node"""
		return self.node.lookup(cap)

	@expose
	def clone(self, cap, options={}, conn=None):
		"""Clone a capability"""
		o = self.node.lookup(cap)
		# cloning always includes the caller fingerprint
		# this restricts revocation
		options.update({'clonefp': conn.peerfp})
		newcap = util.gen_forwarder(self.node.secret, o, self.node.nonce, options=options)
		#self.node.register(o, cap=newcap)
		return self.node.refurl(newcap)

	@expose
	def revoke(self, cap, conn=None):
		"""Revoke a previously cloned capability."""
		objid, opts = self.node.decode_cap(cap)
		cfp = opts.get('clonefp', None)
		autofp = opts.get('fp', None)
		if not cfp: raise NodeException('Not a cloned cap.')
		if cfp != conn.peerfp: raise NodeException('Denied.')
		self.node.revoked.add(cap)
		return True

	@expose
	def revoke_option(self, opt, conn):
		self.node.revoked_opts[conn.peerfp].add(opt)
		return True
		
class Node(EventGen):
	def __init__(self, cert=None, eventloop=None):
		EventGen.__init__(self)
		self.eventloop = eventloop if eventloop != None else evloop
		self.eventloop.shutdown_callback(self._shutdown_request)
		self.cert = cert
		self.x509, self.fp = util.load_cert(self.cert) if cert else (None, 'none')
		self.secret = util.filehash(self.cert)[:16] if cert else 'A' * 16

		logging.debug('Node fingerprint {0}'.format(self.fp))
		print('Node fingerprint {0}'.format(self.fp))
		self.verify_hook = None

		self.connections = set()
		self.peers = {}
		self.listeners = set()
		self._closing = False
		self._shutdown = False
		self.timeoutseconds = 7.0
		self.exports = {}
		self.directcaps = {}
		self.revoked = set()
		self.revoked_opts = collections.defaultdict(set)

		self.nonce = (util.rand32()<<32) | util.rand32()

		self.register(nodeFunctions(self), cap='$node')

	def verify_peer(self, ok, store, *args, **kwargs):
		if self.verify_hook: return self.verify_hook(ok, store, *args, **kwargs)
		return True

	def register(self, obj, options=None, cap=None):
		self.exports[id(obj)] = obj
		if cap: self.directcaps[cap] = obj
		else: cap = util.gen_forwarder(self.secret, obj, self.nonce, options=options)
		return cap

	def refurl(self, ref):
		ports = [i.sock.getsockname()[1] for i in self.listeners]
		hints = ','.join(['{0}:{1}'.format(i[0], i[1]) for i in itertools.product(self.eventloop.hints, ports)])
		return 'pwrcall://{0}@{1}/{2}'.format(self.fp, hints, ref.encode('base64').strip())

	def option_revoked(self, opts):
		if not opts: return False
		if opts and not isinstance(opts, dict):
			print 'options not a dict:', type(opts), opts
			return False
		cfp = opts.pop('clonefp', None)
		if not cfp: return False
		for i in opts.items():
			if i != () and i in self.revoked_opts[cfp]: return True
		return False

	def lookup(self, ref):
		# if ref is unicode, encode latin1
		if type(ref) == unicode: ref = ref.encode('latin1')
		if ref in self.revoked: raise NodeException('Invalid object reference used.')
		o = self.directcaps.get(ref, None)
		if o: return o

		try:
			objid, options = self.decode_cap(ref)
			if self.option_revoked(options): raise NodeException('Invalid object reference used.')
			o = self.exports.get(objid, None)
			if not o: raise NodeException('Invalid object reference used.')
			if isinstance(o, weakref.ref):
				o = o()
				if not o: raise NodeException('Object has gone away.')
		except NodeException, e:
			raise
		except Exception, e:
			traceback.print_exc()
			raise NodeException('Internal Server Error.')
		else:
			return o

	def decode_cap(self, cap):
		try: nonce, objid, opts = util.cap_from_forwarder(self.secret, cap)
		except Exception, e: raise NodeException('Invalid capability.')
		if nonce != self.nonce:	raise NodeException('Nonce from message incorrect.')
		# TODO: somehow give options to user
		return objid, opts

	def shutdown(self, reason=NodeException('Server shutdown.')):
		if self._shutdown:
			return

		self._closing = True
		for c in self.connections: c.close()
		for l in self.listeners: l.close()

		self.connections = set()
		self.listeners = set()
		self._shutdown = True

		logging.info('Node shutdown, {0}'.format(reason))

	# this method is given to eventloop as callback
	# so eventloop can tell us if it goes down
	def _shutdown_request(self):
		self.shutdown()

	def _remove_connection(self, c):
		if not self._closing:
			if c in self.connections: self.connections.remove(c)
			else: logging.critical('connection to be removed not in self.connections!')
		if c.peerfp:
			self.peers.pop(c.peerfp, None)
		logging.info('Disconnect by {0}'.format(c.addr))

	def connect(self, host, port):
		logging.info('Connecting to, {0}:{1}'.format(host, port))

		if self.cert: c = self.eventloop.connectssl(host, port, cert=self.cert)
		else: c = self.eventloop.connectplain(host, port)

		rc = RPCConnection(c, (host, port), self)
		self._event('connection', rc, (host, port))
		return rc

	def listen(self, host='', port=0, backlog_limit=5):
		logging.info('Listening on, {0}:{1}'.format(host, port))

		if self.cert: l = self.eventloop.listenssl(host, port, cert=self.cert)
		else: l = self.eventloop.listenplain(host, port)

		l._on('connection', self._new_conn)
		l._on('close', self._listener_closed)
		self.listeners.add(l)

	def _listener_closed(self, l):
		if not self._closing:
			self.listeners.remove(l)

	def _new_conn(self, c, addr):
		rc = RPCConnection(c, addr, self)
		self._event('connection', rc, addr)
		logging.info('New connection from {0}'.format(addr))

	def _connected(self, rc, peerpromise):
		if rc.peerfp in self.peers:
			rc.close()
		else:
			self.peers[rc.peerfp] = rc
			peerpromise._resolve(rc)

	def establish(self, url):
		try:
			fp, hints, cap = util.parse_url(url)
		except:
			logging.critical('Could not parse pwrcall:// URL.')
			p = Promise()
			p._smash(NodeException('Could not parse pwrcall:// URL.'))
			return p

		# look up fingerprint in connections
		# TODO: keep hashmap to find connections more efficiently
		for c in self.connections:
			if c.peerfp == fp:
				logging.debug('Had a connection to that Node, reusing to get obj.')
				p = Promise()
				p._resolve( Referenced(c, cap) )
				return p

		def on_connected(conn, p, c, fp):
			if conn.peerfp == fp:
				p._resolve(Referenced(conn, c))
			else:
				p._smash(NodeException('Peer public key mismatch: {0}.'.format(conn.peerfp)))

		p1 = Promise()
		p2 = Promise()
		p1._when(on_connected, p2, cap, fp)
		for ip, port in hints:
			rc = self.connect(ip, port)
			rc.onready()._when(self._connected, p1)
			def smash_p2(r):
				if not p2._result: p2._smash(NodeException(r))
			rc._on('close', smash_p2)

		return p2


class RPCConnection(EventGen):
	def __init__(self, conn, addr, node):
		EventGen.__init__(self)
		self.conn = conn
		self.addr = addr
		self.node = node

		self.out_requests = {}
		self.exports = {}
		self.readypromise = Promise()
		self.last_msgid = 0
		self.livesign = time.time()
		self.negotiated = False
		self.remote_info = ''
		self.peerfp = 'none'

		self.unpacker = serialize.PwrUnpacker(self)
		self.packer = serialize.PwrPacker(self, self.gen_cap)
		self.node.connections.add(self)

		conn._on('read', self.io_in)
		conn._on('close', self.closed)
		conn._on('verify', self.node.verify_peer)
		conn.onready()._when(self.negotiate)

	def onready(self):
		return self.readypromise

	def node(self):
		return Referenced(self, '$node')

	def negotiate(self, conn=None):
		self.peerfp = self.conn.peerfp if hasattr(self.conn, 'peerfp') else 'plain'
		self.conn.write(info.gen_banner())

	def ready(self):
		self.negotiated = True
		logging.info("Connected to remote {0} ({1}).".format(self.peerfp, self.remote_info))
		self.readypromise._resolve(self)
		self._event('ready')
		self.keepalive()

	def keepalive(self):
		def ping_response(r):
			self.livesign = time.time()

		if not self.conn._closed:
			if time.time() - self.livesign > self.node.timeoutseconds:
				self.logclose('Connection timeout.')
			else:
				p = self.call('%ping', 'ping')
				p._except(ping_response)
				self.node.eventloop.later(self.node.timeoutseconds-2, self.keepalive)

	def closed(self, reason):
		self.node._remove_connection(self)
		logging.info('Connection closed, {0}'.format(reason))
		for p in self.out_requests.values():
			p._smash(NodeException('Connection closed, {0}'.format(reason)))
		self._event('close', reason)
		
	def close(self, reason=None):
		if not self.conn._closed:
			if reason: self.conn._close(reason)
			else: self.conn.close()

	def logclose(self, msg):
		logging.warn(msg)
		self.close(NodeException(msg))
		return

	def io_in(self, data):
		if not self.negotiated:
			if '\n' in data:
				info, data = data.split('\n', 1)
				self.remote_info += info
				self.ready()
				if not data: return
			else:
				self.remote_info += data
				if len(self.remote_info) > 100: self.logclose('Invalid info string received. Dropping connection.')
				return
		
		try: self.unpacker.feed(data)
		except NodeException as e: return self.close(e)
		for item in self.unpacker:
			if not type(item) in (list, tuple) or len(item) < 4:
				return self.logclose('Invalid data received. Dropping connection.')

			opcode, rest = item[0], item[1:]
			handler = None
			if opcode == RPC_REQUEST: handler = self.request
			elif opcode == RPC_RESPONSE: handler = self.response
			elif opcode == RPC_NOTIFY: handler = self.notify

			if not handler:	return self.logclose('Invalid opcode. Dropping connection.')
			try:
				handler(*rest)
			except TypeError as e:
				return self.logclose('Invalid item received. {0}'.format(e))

	def do_call(self, o, method, params):
		fn = getattr(o, method, None)
		if not fn or not hasattr(fn, 'exposed'):
			raise NodeException('Object has no such method: {0}'.format(method))

		argspec = inspect.getargspec(fn)
		if argspec.args and argspec.args[-1] == 'conn':
			return fn(*params, conn=self)
		else:
			return fn(*params)

	def response(self, msgid, error, result):
		if msgid in self.out_requests:
			p = self.out_requests.pop(msgid)
			if error: p._smash(error)
			else: p._resolve(result)
		else:
			logging.warn('WEIRD! msgid from response not in out_requests')
			logging.info('Result on msgid {0}: err {1}, result {2}'.format(msgid,error,result))
		
	def request(self, msgid, ref, method, params=[]):
		try:
			obj = self.node.lookup(ref)
		except NodeException as e:
			self.send_response(msgid, str(e), None)
			return
			
		if isinstance(obj, Referenced):
			# now this means we exported a referenced, that came from someone else
			# ask him to fulfill the request
			p = obj.call(method, *params)
			p._when(lambda x: self.send_response(msgid, None, x))
			p._except(lambda x: self.send_response(msgid, x, None))
		else:
			try:
				r = self.do_call(obj, method, params)
			except NodeException as e:
				self.send_response(msgid, str(e), None)
			except Exception as e:
				self.send_response(msgid, 'An exception occurred.', None)
				traceback.print_exc()
			else:
				if isinstance(r, Promise):
					def send_delayed(result):
						self.send_response(msgid, None, result)
					def send_error_delayed(e):
						self.send_response(msgid, str(e), None)

					r._when(send_delayed)
					r._except(send_error_delayed)
				else:
					self.send_response(msgid, None, r)
					

	def notify(self, ref, method, params=[]):
		try:
			obj = self.node.lookup(ref)
		except NodeException as e:
			logging.warn('Exception on incoming notify: {0}'.format(e))
			return

		if isinstance(obj, Referenced):
			try:
				obj.notify(method, *params)
			except Exception as e:
				logging.critical('Exception caused by connection {0}. Closing it.'.format(self.conn.addr))
				self.close()
		else:
			try:
				self.do_call(obj, method, params)
			except NodeException as e:
				logging.warn('Exception on incoming notify: {0}'.format(e))

	def send_response(self, msgid, error, result):
		msg = self.packer.pack([RPC_RESPONSE, msgid, error, result])
		self.conn.write(msg)

	def send_request(self, msgid, ref, method, params):
		try: msg = self.packer.pack([RPC_REQUEST, msgid, ref, method, params])
		except NodeException as e: return self.close(e)
		self.conn.write(msg)

	def send_notify(self, ref, method, params):
		try: msg = self.packer.pack([RPC_NOTIFY, ref, method, params])
		except NodeException as e: return self.close(e)
		self.conn.write(msg)

	def call(self, ref, method, *params):
		self.last_msgid += 1
		callid = self.last_msgid
		p = Promise()
		self.out_requests[callid] = p
		self.send_request(callid, ref, method, params)
		return p

	def gen_cap(self, o, options={}):
		options.update({'fp':self.peerfp})
		t = util.gen_forwarder(self.node.secret, o, self.node.nonce, options=options)
		return t
		
