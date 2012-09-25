
import struct
import logging

from .info import addio

try: import bson
except:
	# msgpack not installed, do not add to supported serializers
	pass
else:
	addio('bson')

	class BsonUnpacker(object):
		def __init__(self, arraycb=None):
			self.arraycb = arraycb
			self.buf = ''

		def feed(self, data):
			self.buf += data

		def unpack(self):
			if len(self.buf) < 4: raise StopIteration('stop')
			framelen = struct.unpack('<i', self.buf[:4])[0]

			if len(self.buf) < framelen: raise StopIteration('stop')

			rest, self.buf = self.buf[:framelen], self.buf[framelen:]
			if not bson.is_valid(rest):
				logging.critical('Invalid BSON in frame from remote! content: {0}'.format(repr(rest)))
				return self.unpack()

			dec = bson.BSON(rest).decode()
			return dec['data']

	class BsonPacker(object):
		def pack(self, o):
			return bson.BSON.encode({'data': o})

