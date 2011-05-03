# Set the filename
FILE = client

cpwrcli: $(FILE).c
	gcc -lssl -lmsgpack -g -o cpwrcli $(FILE).c

# Target clean
clean:
	rm cpwrcli

