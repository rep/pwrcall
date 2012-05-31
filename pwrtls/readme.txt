pwrtls - inspired by nacl and curvecp (DJB rocks)
=================================================

 - client and server need a long term keypair and generate short-term keypairs for each connection
   authentication options:
	1) server side key is known, clients not authenticated
	2) like 1) but server knows a list of client public keys
	3) server/client supply each other with signatures on their long-term keys by a trustedkey
	4) server and client know a pre-shared symmetric key
	5) no known keys, server key displayed to user for verification and storage (compare SSH)

 - we do three round-trips starting with a client hello
 - optional: the third message (client->server) could include a payload already if needed
 - messages: client_hello_msg, server_hello_msg, client_verify_msg
 - after handshake, we use the short-term keys to encrypt and authenticate each message
 - profit!

==============================
nacl provides:
crypto_box(message, nonce, receiver-public-key, sender-private-key)
	-> asymmetric authenticated encrypted message
crypto_secretbox(message, nonce, key)
	-> symmetric authenticated encrypted message
crypto_sign(message, signkey)
	-> asymmetric signature on message

------------------------------
client_hello_msg:
{
	spub: short-term public key of client,
	OPTIONAL pskhint: identifier for resolving psk,
	OPTIONAL cahint: identifier for trusted pubkey
}

 -> pskhint only sent when client wants psk auth

------------------------------
server_hello_msg:
{
	box: crypto_box({
		spub: short-term public key,
		OPTIONAL pskv: crypto_secretbox(client short-term public key + 1),
		OPTIONAL cav: crypto_sign(long-term public key)
	}),
	lpub: long-term public key
}

 -> box authenticated with long-term key, encrypted for client short-term key
 -> nonce used is "2" (short-term key only valid for this connection)
 -> long-term key is sent in case the client does not yet have it (lookup/display_accept)
 -> pskv is only sent when client wanted psk auth
 -> cav is a signature on the servers long-term key by the trusted key

------------------------------
client_verify_msg:
{
	box: crypto_box({
		lpub: long-term public key,
		v: crypto_box(short-term public key),
		vn: verifybox_nonce,
		OPTIONAL pskv: crypto_secretbox(server short-term public key + 1)
		OPTIONAL cav: crypto_sign(long-term public key)
	})
}

 -> v is verifybox, long-term to long-term key
 -> box authenticated with short-term key, encrypted for server short-term key
 -> the public key is sent to be able to look it up on the server's side
 -> the verifybox vouches for the short-term key used by the client
 -> pskv and cav see server_hello_msg

