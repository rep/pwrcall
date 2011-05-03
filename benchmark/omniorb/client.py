#!/usr/bin/env python
import sys
from omniORB import CORBA
import Math

import random
import time

def randint():
	return random.randint(2**29, 2**30)

orb = CORBA.ORB_init(sys.argv, CORBA.ORB_ID)

ior = sys.argv[1]
obj = orb.string_to_object(ior)

eo = obj._narrow(Math.MathServer)

if eo is None:
	print "Object reference is not an Math::MathServer"
	sys.exit(1)

starttime = time.time()
ctime = time.time()
c = 0
print int(ctime * 1000), c

while ctime - starttime < 60.0:
	a = randint()
	b = randint()
	res = eo.add(a,b)
	ctime = time.time()

	if res != a+b:
		print 'error, res!= a+b', res, a+b
	c += 1
	if c % 1000 == 0:
		print int(ctime * 1000), c

ctime = time.time()
print int(ctime * 1000), c

