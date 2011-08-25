#!/usr/bin/python
# -*- coding: utf8 -*-

import sys
import logging
logging.basicConfig(level=logging.DEBUG)

from pwrcall import loop, unloop, Node, expose
from pwrcall.util import NodeException, parse_url

import imp
import traceback

CERT = 'appsrv.pem'
PORT = 2000

def load_pwrobj(fpath, modname):
	try:
		modobj = imp.load_module(modname, *imp.find_module(modname, [fpath,]))
	except Exception, e:
		logging.warn('exception when importing module')
		traceback.print_exc()
		raise NodeException('Import Exception: {0}'.format(e))

	pwrobj = getattr(modobj, 'pwrobj', None)
	if pwrobj == None:
		logging.warn('imported module has no pwrobj.')
		raise NodeException('Imported module does not define pwrobj.')
	
	return modobj, pwrobj

class App(object):
	def __init__(self, fpath, modname, modref, ref):
		self.fpath = fpath
		self.modname = modname
		self.modref = modref
		self.ref = ref

class Appserver(object):
	def __init__(self):
		self.apps = {}
		self.lastid = 1
		
	@expose
	def new(self, fpath, modname):
		'''
		fpath is the path of the module/package.
		example> fpath: /opt/foo/, modname: bar
		-> imports /opt/foo/bar and registers bar.pwrobj
		'''
		logging.info('new module request: {0}/{1}'.format(fpath, modname))
		modobj, pwrobj = load_pwrobj(fpath, modname)
		logging.info('imported: {0}.{1}'.format(modobj, pwrobj))
		a = App(fpath, modname, modobj, pwrobj)
		self.lastid += 1
		self.apps[self.lastid] = a
		return pwrobj

	@expose
	def list(self):
		return dict([(k, [v.fpath, v.modname, str(v.ref)]) for k,v in self.apps.items()])

	@expose
	def get(self, appid):
		a = self.apps.get(appid, None)
		if a == None:
			raise NodeException('Nonexisting app.')
		return a.ref

	@expose
	def restart(self, appid):
		a = self.apps.get(appid, None)
		if a == None:
			raise NodeException('Nonexisting app.')
		nmod, nref = load_pwrobj(a.fpath, a.modname)
		a.modref = nmod
		a.ref = nref
		return nref
		

if __name__ == '__main__':
	n = Node(cert=CERT)
	n.listen(port=PORT)
	appsrvobj = Appserver()
	ref = n.register(appsrvobj)
	print 'appserver at', n.refurl(ref)

	loop()

