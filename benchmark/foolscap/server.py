from foolscap.api import Referenceable, Tub
from twisted.internet import reactor

class MathServer(Referenceable):
    def remote_add(self, a, b):
        return a+b

myserver = MathServer()

tub = Tub()
tub.listenOn("tcp:12345")  # start listening on TCP port 12345
tub.setLocation("10.0.0.94:12345")

furl = tub.registerReference(myserver, "math-service")
print "the object is available at:", furl

tub.startService()
reactor.run()

