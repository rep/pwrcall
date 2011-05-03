import sys
import os
import hashlib
import tempfile
import optparse
import logging
logging.basicConfig(level=logging.DEBUG)

from pwrcall import loop, unloop, Node, expose, Promise
from pwrcall.util import NodeException, gen_selfsigned_cert
from evnet import schedule

import gtkdialog

MASTERURL = 'pwrcall://c6db6fac64dd58e7a7a8228e9bc11116397ba58d@137.226.161.210:20001/im'
MASTERURL = 'pwrcall://e7bcae69e9c79aad2f4b8fe1f14bcd52beb4faae@137.226.161.211:20001/im'
DOTPATH = os.path.expanduser('~/.instashare/')
CERTPATH = os.path.join(DOTPATH, 'cert.pem')

class File(object):
	def __init__(self, fname):
		self.fobj = None
		self.fname = fname

	@expose
	def write(self, data):
		if not self.fobj:
			self.fobj = tempfile.NamedTemporaryFile(delete=False, prefix='instasharetmp--{0}--'.format(self.fname), dir=DOTPATH)
		return self.fobj.write(data)

	@expose
	def close(self):
		self.fobj.close()
		print 'sink with path {0}, fname {1} was closed.'.format(self.fobj.name, self.fname)

class Instaclient(object):
	def __init__(self, node):
		self.node = node
		self.ref = node.register_object(self)
		self.pwrurl = node.refurl(self.ref)
		print 'Instaclient exported', self.pwrurl

		gtkdialog.t.create_staticon('./instaicon.svg')
		self.call_master()

	def masterclose(self, r):
		if not self.node._closing and ('timeout' in str(r) or 'ZeroReturn' in str(r)):
			print 'Connection to Instamaster closed. Reconnecting...'
			self.call_master()

	def call_master(self):
		im = self.node.establish(MASTERURL)

		def master_cb(r):
			r.conn._on('close', self.masterclose)
			print 'Successfully connected to Instamaster. Waiting...'
		def master_exc(r):
			print 'Exception on Instamaster promise:', e
			unloop()

		im._when(master_cb)
		im._except(master_exc)

	@expose
	def open(self, filename, conn):
		print 'request to open a file', filename
		sink = File(filename)
		return sink

class Filestreamer(object):
	def __init__(self, src, dst, conn):
		self.src, self.dst = src, dst
		self.conn = conn
		self.done = False
		self.p = Promise()
		self.count = 0
		self.burst = True

		conn.conn._on('writable', self.copy)
		conn.conn._on('close', self.closed)
		schedule(self.copy)

	def copyagain(self, r):
		self.burst = True
		schedule(self.copy)

	def copy(self):
		if self.done or self.conn.conn._closed: return
		if not self.burst: return
		self.count += 1

		d = self.src.read(16384)
		if not d:
			print 'EOF on src, sending close, local close, done'
			p2 = self.dst.call('close')
			def done(r):
				self.p._resolve(True)
				self.conn.close()
			p2._when(done)

			self.done = True
			self.src.close()
			return

		if self.count == 10:
			self.burst = False
			self.count = 0
			p = self.dst.call('write', d)
			p._when(self.copyagain)
		else:
			p = self.dst.notify('write', d)

	def closed(self, e):
		print 'connection closed', e
		if not self.done:
			self.p._smash('Closed, but not done, yet.')


def opts():
	usage = """usage:
	%prog listen
		- registers with master and waits for incoming files
	%prog send <target> <filepath>
		- attempts to send <filepath> to <target>
"""
	parser = optparse.OptionParser(usage=usage)

	options, args = parser.parse_args()

	if len(args) < 1:
		parser.error('Please read usage hints on how to INSTASHARE.')

	action, args = args[0], args[1:]
	if action not in ['listen', 'send']:
		parser.error('Please read usage hints on how to INSTASHARE.')

	if action == 'send':
		if len(args) != 2:
			parser.error('Please read usage hints on how to INSTASHARE.')

	if not setup_dotdir():
		parser.error('Could not create dotdir {0}, exiting.'.format(DOTDIR))

	return options, action, args
	
def main(options, action, args):
	n = Node(cert=CERTPATH)

	if action == 'listen':
		ic = Instaclient(n)
		loop()
	elif action == 'send':
		targetcap, fp = args

		if not (os.path.exists(fp) and os.path.isfile(fp)):
			print fp, 'not a file'
			return 1

		im = n.establish(MASTERURL)

		def established(rim):
			p = rim.call('open', targetcap)

			def donecb(r):
				print 'done:', r
				n.shutdown()
				unloop()

			def prsink(r):
				print 'sink:' , r
				r.notify('init', os.path.basename(fp))
				fs = Filestreamer(open(fp, 'rb'), r, rim.conn)
				fs.p._when(donecb)
				fs.p._except(donecb)

			def prexcept(e):
				print 'Error:', e
				n.shutdown()
				unloop()

			p._when(prsink)
			p._except(prexcept)

		im._when(established)
		loop()

	return 0

def setup_dotdir():
	if not (os.path.exists(DOTPATH) and os.path.isdir(DOTPATH)):
		print 'Creating directory', DOTPATH, '...'
		try:
			os.mkdir(DOTPATH, 0700)
		except:
			return False

	if not (os.path.exists(CERTPATH) and os.path.isfile(CERTPATH)):
		print 'Generating self-signed certificate...'
		try:
			crt = gen_selfsigned_cert()
			open(CERTPATH, 'w').write(crt)
		except:
			return False

	return True

if __name__ == '__main__':
	options, action, args = opts()
	try:
		sys.exit(main(options, action, args))
	except KeyboardInterrupt:
		sys.exit(0)

