#!/usr/bin/env python

import sys
from omniORB import CORBA, PortableServer
import Math, Math__POA

class Math_i (Math__POA.MathServer):
	def add(self, a, b):
		#print "add() called with a,b:", a,b
		res = a+b
		return res

orb = CORBA.ORB_init(sys.argv, CORBA.ORB_ID)
poa = orb.resolve_initial_references("RootPOA")

ei = Math_i()
eo = ei._this()

print 'objstring', orb.object_to_string(eo)

poaManager = poa._get_the_POAManager()
poaManager.activate()

orb.run()

