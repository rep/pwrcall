
import sys
import random
import time

def randint():
	return random.randint(2**29, 2**30)

from jsonrpc.proxy import ServiceProxy

sp = ServiceProxy('jsonrpc://10.0.0.94:10030')
starttime = time.time()
ctime = time.time()
c = 0
print int(ctime*1000), c

while ctime - starttime < 60.0:
	a = randint()
	b = randint()
	res = sp.add(a,b)
	ctime = time.time()

	if res != a+b:
		print 'error, res!= a+b', res, a+b

	c += 1
	if c % 1000 == 0:
		print int(ctime*1000), c
	
ctime = time.time()
print int(ctime*1000), c

