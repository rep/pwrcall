import xmlrpclib
import sys
import random
import time

def randint():
	return random.randint(2**29, 2**30)

proxy = xmlrpclib.ServerProxy("http://{0}:10010/".format(sys.argv[1]))

starttime = time.time()
ctime = time.time()
c = 0
print int(ctime*1000), c

while ctime - starttime < 60.0:
	a = randint()
	b = randint()
	res = proxy.add(a,b)
	ctime = time.time()

	if res != a+b:
		print 'error, res!= a+b', res, a+b
		break

	c += 1
	if c % 1000 == 0:
		print int(ctime*1000), c
	
ctime = time.time()
print int(ctime*1000), c
