

class Service:
    def add(self, a, b):
        return a+b

from jsonrpc.socketserver import ThreadedTCPServiceServer

ThreadedTCPServiceServer(Service()).serve(('0.0.0.0', 10030))

