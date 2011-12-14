
from .info import addio

try: from msgpack import Packer, Unpacker
except:
	# msgpack not installed, do not add to supported serializers
	pass
else:
	addio('msgpack')

	class MsgUnpacker(Unpacker):
		def __init__(self, cb):
			self.cb = cb

			def listhook(obj):
				return self.cb(obj)
			self.listhook = listhook

			Unpacker.__init__(self, list_hook=self.listhook)

	class MsgPacker(Packer):
		def __init__(self, default):
			self.default = default
			Packer.__init__(self, default=self.default)

