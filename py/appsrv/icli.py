
import sys
from IPython.Shell import IPShellEmbed
from evnet import pyevThread
from pwrcall import Node, expose, loop, unloop
from pwrcall.util import NodeException, parse_url

CERT = 'clientside.pem'
t = pyevThread()
t.start()
n = Node(cert=CERT)
ipshell = IPShellEmbed()

def establish(pwrurl):
	return t.blockingCall(n.establish, pwrurl)

def pwrcall(obj, fn, *args):
	return t.blockingCall(obj.call, fn, *args)	

if __name__ == '__main__':
	ipshell.set_banner(
'''pwrcall Interactive Shell
-------------------------
starts up a evnet loop and pwrcall Node
use the Node through the t.blockingCall function''')
	ipshell.set_exit_msg('Exit.')
	ipshell()
	sys.exit(0)

