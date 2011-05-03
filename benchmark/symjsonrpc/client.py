#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

import symmetricjsonrpc, socket

import random
import time

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

			ctime = time.time()
		
			if c % 1000 == 0:
				print int(ctime*1000), c
			
			if ctime - starttime < 60.0:
				startcall()
			else:
				print int(ctime*1000), c
				client.shutdown()
		
			return 

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('10.0.0.94', 4712))
client = PingRPCClient(s)

def startcall():
	a = randint()
	b = randint()
	client.request("add", params=[a, b])

c = 0
starttime = time.time()
ctime = time.time()
print int(ctime*1000), c

for i in range(10):
	startcall()

client.join()

