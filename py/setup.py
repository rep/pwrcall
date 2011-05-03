import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup

import sys, os

def read_file(name):
	return open(os.path.join(os.path.dirname(__file__),name)).read()

extra = {}
if sys.version_info >= (3,):
	extra['use_2to3'] = True

try: readme = read_file('README.md')
except: readme = 'pwrcall'

setup(
	name='pwrcall',
	version = '1.0-1',
	description='pwrcall is a framework for secure distributed function calls',
	long_description=readme,
	classifiers=['Development Status :: 4 - Beta','License :: OSI Approved :: MIT License','Programming Language :: Python','Topic :: Software Development :: Libraries :: Python Modules'], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	author='Mark Schloesser',
	author_email='ms@mwcollect.org',
	license = "MIT/BSD/GPL",
	keywords = "pwrcall evnet pyev network asynchronous nonblocking event rpc distributed",
	url = "https://github.com/rep/pwrcall",
	install_requires = ['evnet>=1.0-4', 'pyOpenSSL>=0.10-1', 'pycrypto>=2.0.1', 'msgpack-python>=0.1.9', 'pyev>=0.5.3-3.8'],
	packages = ['pwrcall',],
	**extra
)

