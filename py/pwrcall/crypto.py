
import os

def encrypt_openssl(*args, **kwargs): raise Exception("Function not available, install needed dependencies!")
def decrypt_openssl(*args, **kwargs): raise Exception("Function not available, install needed dependencies!")
def encrypt_nacl(*args, **kwargs): raise Exception("Function not available, install needed dependencies!")
def decrypt_nacl(*args, **kwargs): raise Exception("Function not available, install needed dependencies!")
def encrypt(*args, **kwargs): raise Exception("Function not available, install needed dependencies!")
def decrypt(*args, **kwargs): raise Exception("Function not available, install needed dependencies!")


try:
	import Crypto.Cipher.AES
	import OpenSSL.crypto
except:
	pass
else:
	def encrypt_openssl(data, secret):
		a = Crypto.Cipher.AES.new(secret, Crypto.Cipher.AES.MODE_CFB, IV=secret)
		return a.encrypt(data)

	def decrypt_openssl(data, secret):
		a = Crypto.Cipher.AES.new(secret, Crypto.Cipher.AES.MODE_CFB, IV=secret)
		return a.decrypt(data)

	encrypt = encrypt_openssl
	decrypt = decrypt_openssl


try:
	import nacl
except:
	pass
else:
	def secretboxnonce():
		return os.urandom(nacl.crypto_secretbox_NONCEBYTES)

	def encrypt_nacl(data, secret):
		n = secretboxnonce()
		return secretboxnonce + nacl.crypto_secretbox(data, n, secret)

	def decrypt_nacl(data, secret):
		n, data = data[:nacl.crypto_secretbox_NONCEBYTES], data[nacl.crypto_secretbox_NONCEBYTES:]
		return nacl.crypto_secretbox_open(data, n, secret)

	encrypt = encrypt_nacl
	encrypt = encrypt_nacl

