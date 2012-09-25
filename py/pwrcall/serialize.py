
import logging
import inspect
import weakref

from .util import NodeException, Referenced
from .info import addio, choose_ioproto

# import serializers
import serialize_bson
import serialize_msgpack

# json is python stdlib \o/
import json
addio('json')

MAXLEN = 1024*1024

class JsonPacker(json.JSONEncoder):
	def __init__(self, defhook, *args, **kwargs):
		json.JSONEncoder.__init__(self, *args, **kwargs)
		self.defhook = defhook
	
	def default(self, o):
		return self.defhook(o)

	def pack(self, o):
		return self.encode(o)

class JsonUnpacker(object):
	def __init__(self, arraycb):
		self.arraycb = arraycb
		self.jdec = json.JSONDecoder(object_hook=self.objcb)
		self.buf = ''

	def objcb(self, o):
		if '_pwrobj' in o:
			return self.arraycb(['_pwrobj',] + o['_pwrobj'])
		return o

	def feed(self, data):
		self.buf += data
	def unpack(self):
		try: pyobj, index = self.jdec.raw_decode(self.buf)
		except ValueError:
			if len(self.buf) > MAXLEN: return self._close('buffer > MAXLEN.')
			raise StopIteration('stop')

		self.buf = self.buf[index:]
		return pyobj

class PwrUnpacker(object):
	def __init__(self, conn):
		self.conn = conn
		self.oseen = {}
		self.cseen = {}
		self._realunpacker = None

	@property
	def realunpacker(self):
		if not self._realunpacker:
			# depending on conn.remote_info, init serializer
			ioproto = choose_ioproto(self.conn.remote_info)
			if not ioproto: raise NodeException('no ioproto possible?')
			if ioproto == 'msgpack':
				self._realunpacker = serialize_msgpack.MsgUnpacker(self.array_cb)
			elif ioproto == 'bson':
				self._realunpacker = serialize_bson.BsonUnpacker()
			elif ioproto == 'json':
				self._realunpacker = JsonUnpacker(self.array_cb)
			else:
				raise NodeException('unknown ioproto chosen? not possible!')
		return self._realunpacker

	def array_cb(self, o):
		if len(o) > 0 and o[0] == '_pwrobj':
			if len(o) == 2:
				_, ref = o
				if not ref in self.oseen:
					raise NodeException('Missing info on pwrcall object.')
				return self.oseen[ref]
			elif len(o) == 4:
				_, ref, cname, attrs = o
				if not cname in self.cseen:
					raise NodeException('Missing class info in pwrcall object.')
				cdoc, funcs = self.cseen[cname]
				r = Referenced( self.conn, ref, cname, cdoc, funcs, attrs )
				self.oseen[ref] = r
				return r
			elif len(o) == 6:
				_, ref, cname, cdoc, funcs, attrs = o
				r = Referenced( self.conn, ref, cname, cdoc, funcs, attrs )
				self.cseen[cname] = (cdoc, funcs)
				self.oseen[ref] = r
				return r
			else:
				raise NodeException('Invalid pwrcall object received.')

		return o

	def feed(self, data):
		self.realunpacker.feed(data)

	def __iter__(self):
		return self

	def next(self):
		return self.unpack()

	def unpack(self):
		self.oseen = {}
		self.cseen = {}
		return self.realunpacker.unpack()
	
class PwrPacker(object):
	def __init__(self, conn, capgen):
		self.conn = conn
		self.capgen = capgen
		self.cseen = set()
		self.oseen = {}
		self._realpacker = None
	
	@property
	def realpacker(self):
		if not self._realpacker:
			# depending on conn.remote_info, init serializer
			ioproto = choose_ioproto(self.conn.remote_info)
			if not ioproto: raise NodeException('no ioproto possible?')
			if ioproto == 'msgpack':
				self._realpacker = serialize_msgpack.MsgPacker(self.default)
			elif ioproto == 'bson':
				self._realpacker = serialize_bson.BsonPacker()
			elif ioproto == 'json':
				self._realpacker = JsonPacker(self.default)
			else:
				raise NodeException('unknown ioproto chosen? not possible!')
		return self._realpacker

	def default(self, o):
		ref = self.oseen.get(o, None)
		if ref:
			return ('_pwrobj', ref)

		if isinstance(o, Referenced):
			functions = [(key,) + value for key, value in o.functions.items()]
			attrs = [(key, value) for key, value in o.attrs.items()]
			classname = o.classname
			classdoc = o.__doc__
			cseen = classname in self.cseen
		else:
			functions = []
			attrs = []
			exposed_attrs = getattr(o, '_exposed_attrs', [])
			classname = o.__class__.__name__
			classdoc = o.__class__.__doc__
			cseen = classname in self.cseen

			for name,member in inspect.getmembers(o):
				if hasattr(member, '__call__'):
					if not cseen:
						nname = getattr(member, 'exposed', None)
						if nname:
							args = inspect.getargspec(member).args
							if hasattr(member, 'im_func'):
								args = args[1:]
							functions.append( (nname, args, member.__doc__) )
				else:
					if name in exposed_attrs:
						attrs.append( (name, member) )
		# end if

		ref = self.capgen(o)
		self.oseen[o] = ref

		if cseen:
			return ('_pwrobj', ref, classname, attrs)

		if not functions and not attrs:
			logging.warn('Serializing object without exposed functions/attributes. Sure this is intended?')
		self.cseen.add(classname)
		return ('_pwrobj', ref, classname, classdoc, functions, attrs)

	def pack(self, o):
		self.cseen = set()
		self.oseen = {}
		tmp = self.realpacker.pack(o)
		for obj in self.oseen:
			self.conn.node.exports[id(obj)] = weakref.ref(obj)
			self.conn.exports[id(obj)] = obj
		return tmp


