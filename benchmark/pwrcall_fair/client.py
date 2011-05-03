import sys
from pwrcall import loop, unloop, Node, expose
import random
import time

def randint():
	return random.randint(2**29, 2**30)

def printexception(r):
	print 'exc:', r
	n.shutdown()
	unloop()

def startcall():
	a = randint()
	b = randint()
	p = math.call('add', a, b)
	p._when(printresult, a, b)

def printresult(res, a,b):
	global c
	if res != a+b:
		print 'error, res!= a+b', res, a+b
		n.shutdown()
		unloop()

	c += 1
	ctime = time.time()

	if c % 1000 == 0:
		print int(ctime*1000), c
	
	if ctime - starttime < 60.0:
		startcall()
	else:
		print int(ctime*1000), c
		n.shutdown()
		unloop()


n = Node(cert='cert2.pem')
math = n.establish(sys.argv[1])
math._except(printexception)

c = 0
starttime = time.time()
ctime = time.time()
print int(ctime*1000), c

startcall()

loop()

