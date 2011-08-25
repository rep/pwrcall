
from pwrcall import expose, Promise
from sp import Process

class Cookie(object):
	def __init__(self, p):
		self.p = p
		self.stdout = ''
		self.stderr = ''
		self.closereason = None
		self.retcode = None
		self.promise = Promise()
		p._on('read', self.stdout)
		p._on('readerr', self.stderr)
		p._on('closed', self.close)

	def resolve(self):
		self.promise._resolve([self.retcode, self.closereason, self.stdout, self.stderr])

	def stdout(self, data):
		print 'stdout', data
		self.stdout += data

	def stderr(self, data):
		print 'stderr', data
		self.stderr += data
		
	def closed(self, e):
		print 'closed', e
		self.closereason = e
		self.retcode = self.p.p.returncode
		self.resolve()

class Spawner(object):
	def __init__(self):
		self.procs = set()

	@expose
	def run(self, args, stdin=None):
		p = Process(args)
		c = Cookie(p)
		self.procs.add(c)
		if stdin != None:
			p.write(stdin)

		def done(r):
			self.procs.remove(c)
		c.promise._when(done)
		return c.promise

pwrobj = Spawner()

