#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import sys
import re
import urlparse
import time
import logging
logging.basicConfig(level=logging.DEBUG)

from pwrcall import loop, unloop, Node
from pwrcall.util import NodeException, parse_url

from evnet import later, listenplain

IP = '127.0.0.1'
PORT = 2001
MAX_BUF = 4096
STATICDIR = './static/'

HTTP_OK = 200
HTTP_BADREQUEST = 400
HTTP_NOTFOUND = 404

HTTP_CODEMAP = {
	HTTP_OK: 'OK',
	HTTP_BADREQUEST: 'Bad request',
	HTTP_NOTFOUND: 'Not found',
}

REGEX_PATH = re.compile('^(GET|POST) (.+) HTTP/1.[01]$')
REGEX_LENGTH = re.compile('^Content-Length: (\d+)$')

def parse_request(buf):
	method, path, length = None, None, 0
	for l in buf.splitlines():
		t = REGEX_PATH.match(l)
		if t:
			method, path = t.groups()
			continue
		else:
			u = REGEX_LENGTH.match(l)
			if u:
				length = t.groups()
				continue

	if not method or not path:
		return False
	return str(method), str(path), length

def response_header(statuscode, length, ct='text/html', headers={}):
	headers.update({'Connection': 'keep-alive'})
	return '''HTTP/1.1 {0} {1}
Server: pwrcall httpd
Content-Type: {2}; charset=utf-8
Content-Length: {3}
{4}

'''.format(
	statuscode, HTTP_CODEMAP[statuscode], ct, length,
	'\n'.join(['{0}: {1}'.format(key, value) for key,value in headers.items()])
	)

def page400():
	data = '<h1>Bad request!</h1>'
	return response_header(400, len(data)) + data
def page404():
	data = '<h1>Not found!</h1>'
	return response_header(404, len(data)) + data

def page200(payload):
	return response_header(200, len(payload)) + payload

def content_type(filename):
	front, ext = os.path.splitext(filename)
	return {'.js': 'application/javascript', '.css': 'text/css', '.html': 'text/html'}.get(ext, 'text/plain')

class WebConn(object):
	def __init__(self, conn, addr, srv):
                self.conn = conn
                self.addr = addr
                self.srv = srv
		self.buf = bytearray()
		self.state = 0
		self.method = None
		self.path = None
		self.length = None

		conn._on('read', self.io_in)

	def io_in(self, data):
		self.buf.extend(data)
		if len(self.buf) > MAX_BUF:
			self.conn.write(page400())
			self.conn.close()

		if self.state == 0:
			if '\n\n' in self.buf:
				head, self.buf = self.buf.split('\n\n', 1)
			elif '\r\n\r\n' in self.buf:
				head, self.buf = self.buf.split('\r\n\r\n', 1)
			else:
				return
			r = parse_request(head)
			if r == False:
				self.conn.write(page400())
				self.conn.close()
			else:
				self.method, self.path, self.length = r
				self.state = 1
				later(0.0, self.io_in, b'')

		elif self.state == 1:
			if len(self.buf) >= self.length:
				self.dispatch()

	def dispatch(self):
		print 'DEBUG:', self.method, self.path, self.length
		print 'DATA:', self.buf

		path = urlparse.urlparse(self.path).path.lstrip('/')

		if path.startswith('static/'):
			self.send_staticfile(path[7:])
		else:
			fn = getattr(self.srv, self.method + '_' + path, None)
			if fn:
				fn(self, self.buf)
			else:
				self.conn.write(page404())

		self.buf = bytearray()
		self.state = 0

	def send_staticfile(self, filename):
		sfiles = os.listdir(STATICDIR)
		fp = os.path.join(STATICDIR, filename)
		if os.path.exists(fp) and os.path.isfile(fp):
			fl = os.stat(fp).st_size
			fd = open(fp, 'rb')
			self.conn.write(response_header(200, fl, ct=content_type(filename)))
			for chunk in fd:
				self.conn.write(chunk)
		else:
			self.conn.write(page404())

class pwrweb(object):
	def __init__(self):
		self.listener = listenplain(host=IP, port=PORT)
		self.listener._on('close', self._lclose)
		self.listener._on('connection', self._newconn)

	def _newconn(self, c, addr):
		logging.debug('Connection from {0}.'.format(addr))
		tc = WebConn(c, addr, self)

	def _lclose(self, e):
		logging.critical('Listener closed ({0}). Exiting.'.format(e))
		unloop()

	def GET_time(self, wc, data):
		wc.conn.write(page200(str(time.time())))

def main():
	pw = pwrweb()
	loop()
	return 0

if __name__ == '__main__':
	sys.exit(main())
