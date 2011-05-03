#!/usr/bin/env python
 
import sys
sys.path.append('./gen-py')
 
from mathbench import Math
from mathbench.ttypes import *
 
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
 
import socket
 
class MathHandler:
	def add(self, a, b):
		return a+b
 
handler = MathHandler()
processor = Math.Processor(handler)
transport = TSocket.TServerSocket(30303)
tfactory = TTransport.TBufferedTransportFactory()
pfactory = TBinaryProtocol.TBinaryProtocolFactory()
 
server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)
 
print "Starting python server..."
server.serve()
print "done!"

