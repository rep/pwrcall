import sys
from pwrcall import loop, unloop, Node, expose, util

n = Node(cert='clientside.pem')
math = n.establish(sys.argv[1])
giftr = n.establish(sys.argv[2])
#math2 = n.connect('127.0.0.1', 10000).rootobj().call('get', sys.argv[1].split('/')[-1])

def printexception(r, msg):
	print 'exc', msg, ':', r
	n.shutdown()
	unloop()

def printresult(result):
	print 'printresult:', result

def revokedone(res):
	print 'revokedone', res

def doneusing(result, m, ccapp):
	print 'giftreceiver is done using object:', result
	fp, hints, cap = util.parse_url(ccapp)
	print 'asking the owner to revoke the cap...'
	revokep = m.conn.call('$node', 'revoke', cap)
	revokep._when(revokedone)
	revokep._except(printexception, 'revoking')

def gotclonecap(ccapp, m):
	print 'got clone cap:', ccapp
	rp = giftr.call('donate', ccapp)
	rp._when(doneusing, m, ccapp)
	rp._except(printexception, 'donating')

def gotmath(m):
	print 'got math, cloning cap...'
	ccapp = m.conn.call('$node', 'clone', m.ref, {'for': 'giftr'})
	ccapp._when(gotclonecap, m)
	ccapp._except(printexception, 'cloning')

#math._except(printexception)
#p = math.call('add', 11, 17)
#p._when(printresult)
math._when(gotmath)
math._except(printexception,'math')
giftr._when(printresult)
giftr._except(printexception, 'giftr')

loop()

