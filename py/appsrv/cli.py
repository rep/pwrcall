import sys
from pwrcall import loop, unloop, Node, expose
from evnet import later

n = Node(cert='clientside.pem')
math = n.establish(sys.argv[1])

def printexception(r):
	print 'exc:', r
	n.shutdown()
	unloop()

def printresult(result):
	print 'printresult:', result

def close(r=None):
	n.shutdown()
	unloop()

math._except(printexception)
p = math.call('new', './module/', 'test')
p._when(printresult)

ap = p.call('add', 4, 5)
ap._when(printresult)

lp = math.call('list')
lp._when(printresult)

later(5.0,close)

loop()

