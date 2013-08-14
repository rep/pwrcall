
import os
import struct
import collections
import weakref
import urlparse
import hashlib

import info
import crypto

try: import msgpack
except: pass

class NodeException(Exception):
	"""Base for Node Exceptions"""

class CallException(Exception):
	"""Call Exception"""


class EventGen(object):
	def __init__(self):
		self._event_subscribers = collections.defaultdict(list)

	def _on(self, name, cb):
		#self._event_subscribers[name].append(WeakMethod(cb))
		self._event_subscribers[name].append(cb)

	def _event(self, name, *args):
		for cb in self._event_subscribers[name]:
			#if cb.alive():
				cb(*args)


class Referenced(object):
	def __init__(self, conn, ref, classname=None, classdoc=None, functions=[], attrs=[]):
		self.conn = conn
		self.ref = ref
		self.classname = classname
		self.__doc__ = classdoc

		self.functions = {}
		for name, sig, doc in functions:
			self.functions[name] = (sig, doc)
		self.attrs = dict(attrs)

	def call(self, method, *params):
		return self.conn.call(self.ref, method, *params)

	def notify(self, method, *params):
		self.conn.send_notify(self.ref, method, params)

def filehash(fpath):
	return hashlib.sha1(open(fpath).read()).digest()

def expose(fn, name=None):
	fn.exposed = name or fn.__name__
	return fn

def rand32():
	return struct.unpack('I', os.urandom(4))[0]

def gen_forwarder(secret, obj, nonce, options={}):
	return crypto.encrypt( msgpack.packb((nonce, id(obj), options)), secret )

# returns (fp, obj, nonce)
def cap_from_forwarder(secret, fwd):
	return msgpack.unpackb( crypto.decrypt(fwd, secret) )

def parse_url(url):
	up = urlparse.urlparse(url)
	hints = []
	if up.netloc:
		try: hints = [(j[0], int(j[1])) for j in [i.split(':') for i in up.netloc.split('@')[1].split(',')]]
		except: pass
	return up.username, hints, up.path.lstrip('/').decode('base64')

def load_cert(cert):
	if not cert:
		return None,''
	if os.path.exists(cert):
		x509 = crypto.OpenSSL.crypto.load_certificate(crypto.OpenSSL.crypto.FILETYPE_PEM, open(cert, 'r').read())
		fp = x509.digest('sha1').replace(':','').lower()
		return x509, fp
	return None, ''

# some support classes for weakly referencing methods
class WeakMethodBound:
	def __init__(self, f):
		self.f = f.im_func
		self.c = weakref.ref(f.im_self)
	def __call__(self, *args):
		if self.c() == None:
			raise TypeError, 'Method called on dead object'
		apply(self.f, (self.c(),) + args)
	def alive(self):
		return (not self.c() == None)

class WeakMethodFree:
	def __init__(self, f):
		self.f = weakref.ref(f)
	def __call__(self, *args):
		if self.f() == None:
			raise TypeError, 'Function no longer exist'
		apply(self.f(), args)
	def alive(self):
		return (not self.f() == None)

def WeakMethod(f):
	try :
		f.im_func
	except AttributeError :
		return WeakMethodFree(f)
	return WeakMethodBound(f)


def gen_selfsigned_cert(c='DE', st='NRW', l='Aachen', o='ITsec', ou='pwrcall', cn=os.urandom(10).encode('hex')):
	k = crypto.OpenSSL.crypto.PKey()
	k.generate_key(crypto.OpenSSL.crypto.TYPE_RSA, 1024)

	# create a self-signed cert
	cert = crypto.OpenSSL.crypto.X509()
	cert.get_subject().C = c
	cert.get_subject().ST = st
	cert.get_subject().L = l
	cert.get_subject().O = o
	cert.get_subject().OU = ou
	cert.get_subject().CN = cn
	cert.set_serial_number(1000)
	cert.gmtime_adj_notBefore(0)
	cert.gmtime_adj_notAfter(10*365*24*60*60)
	cert.set_issuer(cert.get_subject())
	cert.set_pubkey(k)
	cert.sign(k, 'sha1')

	crtpem = crypto.OpenSSL.crypto.dump_certificate(crypto.OpenSSL.crypto.FILETYPE_PEM, cert)
	keypem = crypto.OpenSSL.crypto.dump_privatekey(crypto.OpenSSL.crypto.FILETYPE_PEM, k)

	return '\n'.join([keypem, crtpem])


