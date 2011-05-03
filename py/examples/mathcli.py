import sys
from pwrcall import loop, unloop, Node, expose

n = Node(cert='clientside.pem')
math = n.establish(sys.argv[1])
#math2 = n.connect('127.0.0.1', 10000).rootobj().call('get', sys.argv[1].split('/')[-1])

def printexception(r):
	print 'exc:', r
	n.shutdown()
	unloop()

math._except(printexception)
p = math.call('add', 11, 17)

def printresult(result):
	print 'printresult:', result
	n.shutdown()
	unloop()

p._when(printresult)

loop()

