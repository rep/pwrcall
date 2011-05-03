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

#println((interp.getArgs())[0])
def <util> := <unsafe:java.util.*>
def starttime := <util:makeDate>().getTime()
def randm := <util:makeRandom>(starttime)
# def ctime := <unsafe:java.lang.System.currentTimeMillis>()
# println("time " + <sys>())
var c := 0
println(`$starttime $c`)

def bench() {
	def rm := getObjectFromURI((interp.getArgs())[0])

	def startcall() {
		def a := randm.nextInt()
		def b := randm.nextInt()
		def val := rm <- add(a, b)
		when(val) -> {
			if (val != a+b) {
				println("wrong result")
				println(val)
				println(a+b)
				interp.continueAtTop()
			}
			#println(val)
			def ctime := <util:makeDate>().getTime()
			c += 1
			if (c%1000 == 0) {
				println(`$ctime $c`)
			}
			if (ctime - starttime < 60000) {
				startcall()
			} else {
				interp.continueAtTop()
			}
		}
	}

	startcall()
	startcall()
	startcall()
	startcall()
	startcall()
	startcall()
	startcall()
	startcall()
	startcall()
	startcall()
}

bench()

# bind friend := getObjectFromURI(file.getText())
interp.blockAtTop()

def endtime := <util:makeDate>().getTime()
println(`$endtime $c`)


