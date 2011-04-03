#!/usr/bin/env python

from __future__ import with_statement

from distutils.core import setup
from distutils.command.build_py import build_py
import os.path
import time

PKG_NAME = 'termitheme'
PKG_URL = 'http://www.sapphirepaw.org/termitheme/'
VERSION = '1.5a'
CODENAME = 'By Humans For Humans'
_VERSION_FILE = PKG_NAME + '/version.py'

short_desc = 'Terminal theme importer/exporter'
long_desc = """Imports and exports themes to and from gnome-terminal on Unix
and PuTTY (via sessions in the Registry) on Windows."""

classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Operating System :: Microsoft :: Windows',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: Unix',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Desktop Environment :: Gnome',
    'Topic :: Artistic Software',
    'Topic :: Terminals :: Terminal Emulators/X Terminals',
]


def get_revision ():
    rev = None
    if os.path.exists('.git'):
        try:
            proc = Popen(['git', 'log', '-1', '--pretty=format:%h'],
                         stdout=PIPE)
            output = proc.communicate()[0]
            rev = output.strip()
        except Exception, e:
            pass

    return rev

def write_version (filename, version):
    with open(filename, 'w') as f:
        f.write("version = %s\n" % repr(version))
        f.write("revision = %s\n" % repr(get_revision()))
        f.write("family = %s\n" % repr(CODENAME))
        f.write("build_time = %f\n" % time.time())


class LocalBuildPy (build_py):
    def run (self):
        write_version(_VERSION_FILE, VERSION)
        return build_py.run(self)


def do_setup ():
    setup(cmdclass={'build_py': LocalBuildPy},
          name=PKG_NAME,
          version=version,
          description=short_desc,
          long_description=long_desc,
          author='Chad Daelhousen',
          author_email='release@sapphirepaw.org',
          url=PKG_URL,
          scripts=['bin/' + PKG_NAME],
          license='Apache 2.0',
          packages=[PKG_NAME],
          classifiers=classifiers)

def main(argv=None):
    do_setup()

if __name__ == '__main__':
    main()

