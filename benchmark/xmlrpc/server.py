from SimpleXMLRPCServer import SimpleXMLRPCServer

def add(x,y):
    return x+y

server = SimpleXMLRPCServer(("0.0.0.0", 10010), logRequests=False)
print "Listening on port 8000..."
server.register_function(add, 'add')

server.serve_forever()

