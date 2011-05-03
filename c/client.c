#include <openssl/bio.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <stdio.h>
#include <msgpack.h>

int RPC_REQUEST = 0;
int RPC_RESPONSE = 1;

void write_msgpackobj(BIO* bio, msgpack_sbuffer* buffer) {
	BIO_write(bio, buffer->data, buffer->size);
	msgpack_sbuffer_clear(buffer);
}

void gen_request(msgpack_packer* pk, int msgid, char* object_ref, int a, int b) {
	/* serializes [RPC_REQUEST, 1, <object_ref>, "add", [15, 13]] */
	msgpack_pack_array(pk, 5);
	msgpack_pack_uint64(pk, RPC_REQUEST);
	msgpack_pack_uint64(pk, msgid);
	msgpack_pack_raw(pk, strlen(object_ref));
	msgpack_pack_raw_body(pk, object_ref, strlen(object_ref));
	msgpack_pack_raw(pk, 3);
	msgpack_pack_raw_body(pk, "add", 3);
	msgpack_pack_array(pk, 2);
	msgpack_pack_uint64(pk, a);
	msgpack_pack_uint64(pk, b);
}
void gen_errormsg(msgpack_packer* pk, int msgid) {
	/* serializes [RPC_RESPONSE, <msgid>, <errormsg>, null] */
	msgpack_pack_array(pk, 4);
	msgpack_pack_uint64(pk, 1);
	msgpack_pack_uint64(pk, msgid);
	msgpack_pack_raw(pk, 20);
	msgpack_pack_raw_body(pk, "No requests allowed.", 20);
	msgpack_pack_nil(pk);
}

void pwrcall_client(char * arg1) {
	SSL_CTX* ctx = SSL_CTX_new(SSLv23_client_method());
	SSL* ssl;
	BIO* bio = BIO_new_ssl_connect(ctx);
	if (bio == NULL) {
		printf("Error creating BIO!\n");
		ERR_print_errors_fp(stderr);
		return;
	}

	BIO_get_ssl(bio, &ssl);
	SSL_set_mode(ssl, SSL_MODE_AUTO_RETRY);
	SSL_use_certificate_file(ssl, "cert.pem", SSL_FILETYPE_PEM);
	SSL_use_PrivateKey_file(ssl, "cert.pem", SSL_FILETYPE_PEM);
	BIO_set_conn_hostname(bio, "127.0.0.1:10000");

	if (BIO_do_connect(bio) <= 0) {
		printf("Failed to connect!\n");
		return;
	}

	if (BIO_do_handshake(bio) <= 0) {
		printf("Failed to do SSL handshake!\n");
		return;
	}

	// buffer for received data	
	char buf[16384];
	memset(buf, 0, sizeof(buf));

	// message structure for unpacking
	msgpack_unpacked msg;
	msgpack_unpacked_init(&msg);
	msgpack_sbuffer* buffer = msgpack_sbuffer_new();
	msgpack_packer* pk = msgpack_packer_new(buffer, msgpack_sbuffer_write);

	// send request
	gen_request(pk, 1, arg1, 15, 17);
	write_msgpackobj(bio, buffer);

	while (1) {
		int x = BIO_read(bio, buf, sizeof(buf) - 1);
		if (x == 0) break;
		else if (x < 0) {
			if (!BIO_should_retry(bio)) {
				printf("Read Failed!\n");
				return;
			}
		} else {
			bool success = msgpack_unpack_next(&msg, buf, x, NULL);
			if (!success) {
				printf("msgpack_unpack failed!\n");
				return;
			}
			msgpack_object o = msg.data;
			if (o.via.array.ptr->via.u64 == 0) {
				// we don't handle requests
				gen_errormsg(pk, (o.via.array.ptr+1)->via.u64);
				write_msgpackobj(bio, buffer);
			} else if (o.via.array.ptr->via.u64 == 1) {
				// only the add call response should be received
				printf("call response: %lu\n", (o.via.array.ptr+3)->via.u64);
				break;
			}	
		}
		fflush(stdout);
	}
	fflush(stdout);

	// cleanup
	msgpack_sbuffer_free(buffer);
	msgpack_packer_free(pk);
	msgpack_unpacked_destroy(&msg);
	BIO_free_all(bio);
	SSL_CTX_free(ctx);
	return;
}
 
int main(int argc, char** argv) {
	CRYPTO_malloc_init();
	SSL_library_init();
	SSL_load_error_strings();
	ERR_load_BIO_strings();
	OpenSSL_add_all_algorithms();

	pwrcall_client(argv[1]);
	return 0;
}
