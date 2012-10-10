
import socket
import time
import logging
import traceback

import gevent.server
import gevent.socket
import gevent.event
import gevent.local

from . import rpcnode
from . import util
from . import serialize
from .util import NodeException, CallException, EventGen, Referenced
from .rpcnode import RPC_REQUEST, RPC_RESPONSE, RPC_NOTIFY

import pwrtls

BUFSIZE = 16*1024

class EVException(Exception):
	"""Eventloop Exceptions"""


class ConnTimeout(EVException):
	"""Eventloop Exceptions"""


class StreamServer(gevent.server.StreamServer):
	def close(self, *args, **kwargs):
		self.stop(*args, **kwargs)


class geventLoopAdapter:
	@classmethod
	def later(seconds, cb, *args, **kwargs):
		gevent.core.timer(seconds, cb, *args, **kwargs)


class SockWrap(EventGen):
	def __init__(self, sock):
		EventGen.__init__(self)
		self.sock = sock
		self._closed = False
	def read(self):
		try:
			return self.sock.recv(BUFSIZE)
		except pwrtls.pwrtls_closed:
			return ''
		except socket.error:
			self.close()
			return ''
	def write(self, data):
		try: return self.sock.send(data)
		except pwrtls.pwrtls_closed:
			return ''
		except socket.error:
			self.close()
			return 0
	def _close(self, e):
		if self.sock: self.sock.close()
		self._closed = True
		self._event('close', e)
	def close(self):
		if not self._closed: self._close(EVException('Connection closed.'))


class Node(rpcnode.Node):
	local = gevent.local.local()

	def __init__(self, *args, **kwargs):
		rpcnode.Node.__init__(self, *args, **kwargs)
		self.eventloop = geventLoopAdapter

	def refurl(self, ref):
		return 'pwrcall://{0}@{1}/{2}'.format(self.fp, '', ref.encode('base64').strip())

	def connect(self, host, port):
		logging.info('Connecting to, {0}:{1}'.format(host, port))

		c = gevent.socket.create_connection((host, port))

		return self._new_conn(c, (host, port))

	def connectPTLS(self, host, port, statepath=None):
		logging.info('Connecting to, {0}:{1}'.format(host, port))
		if not statepath: raise NodeException('PTLS needs statepath!')

		c = gevent.socket.create_connection((host, port))
		c = pwrtls.wrap_socket(c, **pwrtls.state_file(statepath))
		c.do_handshake()

		return self._new_conn(c, (host, port))

	def listen(self, host='', port=0, backlog_limit=5):
		def handle(sock, addr):
			self._new_conn(sock, addr)

		l = StreamServer((host, port), handle)
		self.listeners.add(l)
		l.start()

	def listenPTLS(self, host='', port=0, backlog_limit=5, statepath=None):
		if not statepath: raise NodeException('listenPTLS needs statepath!')
		def handle(socket, addr):
			socket = pwrtls.wrap_socket(socket, server_side=True, **pwrtls.state_file(statepath))
			socket.do_handshake()
			self._new_conn(socket, addr)

		l = StreamServer((host, port), handle)
		self.listeners.add(l)
		l.start()

	def _new_conn(self, c, addr):
		rc = RPCConnection(c, addr, self)
		self._event('connection', rc, addr)
		logging.info('New connection: {0}'.format(addr))
		return rc

	def establish(self, url):
		try:
			fp, hints, cap = util.parse_url(url)
		except:
			logging.critical('Could not parse pwrcall:// URL.')
			raise NodeException('Could not parse pwrcall:// URL.')

		# look up fingerprint in connections
		# TODO: keep hashmap to find connections more efficiently
		for c in self.connections:
			if c.peerfp == fp:
				logging.debug('Had a connection to that Node, reusing to get obj.')
				return Referenced(c, cap)

		for ip, port in hints:
			try: c = self.connect(ip, port)
			except socket.error:
				continue

			if c.peerfp == fp: return Referenced(c, cap)
			else: raise NodeException('Peer public key mismatch: {0}.'.format(c.peerfp))

		raise NodeException('Could not establish object connection.')

	def serve_forever(self):
		for l in self.listeners:
			l._stopped_event.wait()

class RPCConnection(rpcnode.RPCConnection):
	def __init__(self, conn, addr, node):
		EventGen.__init__(self)
		self.conn = SockWrap(conn)
		self.addr = addr
		self.node = node

		self.out_requests = {}
		self.exports = {}
		self.last_msgid = 0
		self.livesign = time.time()
		self.remote_info = ''
		self.peerfp = 'none'
		self.buf = ''

		self.unpacker = serialize.PwrUnpacker(self)
		self.packer = serialize.PwrPacker(self, self.gen_cap)
		self.node.connections.add(self)

		self.conn._on('close', self.closed)
		self.negotiate()
		self.wait_for_banner()

	def ready(self):
		self.negotiated = True
		logging.info("Connected to remote {0} ({1}).".format(self.peerfp, self.remote_info))
		self._event('ready')
		self.alivegreenlet = gevent.spawn(self.keepalive)
		self.handlegreenlet = gevent.spawn(self.handle)

	def keepalive(self):
		while True:
			with gevent.Timeout(self.node.timeoutseconds, ConnTimeout) as timeout:
				try:
					r = self.call('%ping', 'ping')
				except ConnTimeout:
					return self.logclose('Connection timeout.')
				except CallException:
					# this is normal, as ping does not exist
					pass
				except NodeException as e:
					# maybe connection was already closed
					logging.info('Keepalive: {0}'.format(e))
					break
				except Exception as e:
					logging.debug('Exception in keepalive: {0}'.format(e))
					traceback.print_exc()
					break
				finally:
					gevent.sleep(self.node.timeoutseconds-2)
			if self.conn._closed: break

	def call(self, ref, method, *params):
		self.last_msgid += 1
		callid = self.last_msgid
		ar = gevent.event.AsyncResult()
		self.out_requests[callid] = ar
		self.send_request(callid, ref, method, params)
		r = ar.get()
		return r

	def wait_for_banner(self):
		tmp = ''
		while not '\n' in tmp:
			if len(tmp) > 100: return self.logclose('Invalid info string received. Dropping connection.')
			tmp += self.conn.read()

		self.remote_info, tmp = tmp.split('\n', 1)
		self.ready()
		self.buf += tmp

	def handle(self):
		data = self.conn.read()
		while data:
			try: self.unpacker.feed(data)
			except NodeException as e: return self.close(e)
			for item in self.unpacker:
				if not type(item) in (list, tuple) or len(item) < 4:
					return self.logclose('Invalid data received. Dropping connection.')

				opcode, rest = item[0], item[1:]
				handler = None
				if opcode == RPC_REQUEST:
					g = gevent.spawn(self.request, *rest)
					g.link_exception(self.handler_exception)
				elif opcode == RPC_RESPONSE:
					self.response(*rest)
				elif opcode == RPC_NOTIFY:
					gevent.spawn(self.notify, *rest)
					g.link_exception(self.handler_exception)
				else:
					return self.logclose('Invalid opcode. Dropping connection.')

			data = self.conn.read()
		return self.logclose('handle finished.')

	def handler_exception(self, *args, **kwargs):
		print 'handler exception:', args, kwargs
		return self.logclose('Invalid item received. {0}'.format(args))

	def request(self, msgid, ref, method, params=[]):
		try:
			obj = self.node.lookup(ref)
		except NodeException as e:
			self.send_response(msgid, str(e), None)
			return

		if isinstance(obj, Referenced):
			# now this means we exported a referenced, that came from someone else
			# ask him to fulfill the request
			try: r = obj.call(method, *params)
			except CallException as e: self.send_response(msgid, str(e), None)
			else: self.send_response(msgid, None, r)
		else:
			obj.conn = self
			Node.local.conn = self
			try:
				r = self.do_call(obj, method, params)
			except NodeException as e:
				self.send_response(msgid, str(e), None)
			except Exception as e:
				self.send_response(msgid, 'An exception occurred.', None)
				traceback.print_exc()
			else:
				self.send_response(msgid, None, r)

	def response(self, msgid, error, result):
		if msgid in self.out_requests:
			ar = self.out_requests.pop(msgid)
			if error: ar.set_exception(CallException(error))
			else: ar.set(result)
		else:
			logging.warn('WEIRD! msgid from response not in out_requests')
			logging.info('Result on msgid {0}: err {1}, result {2}'.format(msgid,error,result))

	def close(self, reason=None):
		if not self.conn._closed:
			if reason: self.conn._close(reason)
			else: self.conn.close()

	def closed(self, reason):
		self.node._remove_connection(self)
		logging.info('Connection closed, {0}'.format(reason))
		ne = NodeException('Connection closed, {0}'.format(reason))
		for ar in self.out_requests.values():
			ar.set_exception(ne)
		#gevent.kill(self.alivegreenlet, exception=ne)
		self._event('close', reason)

