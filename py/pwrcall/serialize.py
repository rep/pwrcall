
import logging
import inspect
import weakref

from msgpack import Packer, Unpacker

from .util import NodeException, Referenced

def hook(o):
	return o

class PwrUnpacker(Unpacker):
	def __init__(self, conn):
		def listhook(obj):
			return self.array_cb(obj)
		self.listhook = listhook

		Unpacker.__init__(self, list_hook=self.listhook)
		self.conn = conn
		self.oseen = {}
		self.cseen = {}

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

	def unpack(self):
		self.oseen = {}
		self.cseen = {}
		return Unpacker.unpack(self)

class PwrPacker(Packer):
	def __init__(self, conn, capgen):
		Packer.__init__(self, default=self.default)
		self.conn = conn
		self.capgen = capgen
		self.cseen = set()
		self.oseen = {}

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
		tmp = Packer.pack(self, o)
		for obj in self.oseen:
			self.conn.node.exports[id(obj)] = weakref.ref(obj)
			self.conn.exports[id(obj)] = obj
		return tmp


