#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

import symmetricjsonrpc, socket

import random
import datetime

def randint():
	return random.randint(2**29, 2**30)

class PingRPCClient(symmetricjsonrpc.RPCClient):
	class Request(symmetricjsonrpc.RPCClient.Request):
		def dispatch_response(self, subject):
			global c
			c += 1
			if subject['error']:
				print 'error?', subject
				client.shutdown()
		
			if c % 1000 == 0:
				print '{1} | calls: {0}'.format(c, datetime.datetime.now())
			
			if datetime.datetime.now() - starttime < datetime.timedelta(0, 60):
				startcall()
			else:
				print '{1} | END calls: {0}'.format(c, datetime.datetime.now())
				client.shutdown()
		
			return 

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('10.0.0.94', 4712))
client = PingRPCClient(s)

client.notify("shutdown")

client.shutdown()

