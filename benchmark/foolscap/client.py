import sys

from foolscap.api import Tub
from twisted.internet import reactor

import random
import time

def randint():
	return random.randint(2**29, 2**30)

def printexception(r):
	print 'exc:', r
	reactor.stop()

def startcall(remote):
	a = randint()
	b = randint()
	d = remote.callRemote("add", a=a, b=b)
	d.addCallback(printresult, a,b, remote)
	d.addErrback(printexception)

def printresult(res, a,b, remote):
	global c
	if res != a+b:
		print 'error, res!= a+b', res, a+b
		reactor.stop()

	c += 1
	ctime = time.time()

	if c % 1000 == 0:
		print int(ctime*1000), c
	
	if ctime - starttime < 60.0:
		startcall(remote)
	else:
		print int(ctime*1000), c
		reactor.stop()

def gotReference(remote):
	startcall(remote)


tub = Tub()
tub.startService()
d = tub.getReference(sys.argv[1])
d.addCallbacks(gotReference, printexception)

c = 0
starttime = time.time()
ctime = time.time()
print int(ctime*1000), c

reactor.run()

