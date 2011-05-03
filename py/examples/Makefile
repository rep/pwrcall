
default:
	openssl req -new -x509 -days 365 -nodes -out serverside.pem -keyout serverside.pem -config cert.cnf
	openssl req -new -x509 -days 365 -nodes -out clientside.pem -keyout clientside.pem -config cert.cnf

# Target clean
clean:
	rm serverside.pem clientside.pem

