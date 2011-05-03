#!/usr/bin/env rune

pragma.syntax("0.9")

# introducer.setVatIdentity(introducer.newVatIdentity())
introducer.onTheAir()

# return the object represented by the URI
def getObjectFromURI(uri)  {return introducer.sturdyFromURI(uri).getRcvr()}

def makeURIFromObject(obj) :String {
    # This implementation assumes a non-persistent single incarnation
    def [sr, _, _] := identityMgr.makeKnown(obj)
    #XXX not a uri if bracketed, bug, markm?
    def bracketed := introducer.sturdyToURI(sr)
    if (bracketed =~ `<@uri>`) {return uri}
    return bracketed
}

def math {
     to add(a, b) {
         return a+b
     }
     to mul(a, b) {
         return a*b
     }
}

println("test")
println(makeURIFromObject(math))
println(interp.getArgs())

# bind friend := getObjectFromURI(file.getText())
interp.blockAtTop()
