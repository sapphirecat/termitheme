import locale
import os.path
import sys
from termitheme import core, commands, version

VERSION = version.version
if version.revision:
    VERSION += " [rev " + version.revision + "]"

def usage (argv):
    prog = os.path.basename(argv[0])
    print "Usage: %s <command> [command arguments...]" % prog
    print
    print "Available commands:"
    for cmd,handler_cls in commands.get_cmds().items():
        handler = handler_cls()
        handler.show_usage(argv[0])
    print
    print "For help on a command, use %s <command> --help" % prog
    print
    return 2

def print_version ():
    print >>sys.stderr, "termitheme version %s" % VERSION
    return 0

# Platform encoding support
# Bust us out of 'C' locale
locale.setlocale(locale.LC_ALL, '')
charset = None
try:
    charset = locale.nl_langinfo(locale.CODESET)
except AttributeError:
    # fall back to ANSI code page on win32
    if sys.platform.startswith("win"):
        charset = 'mbcs'
if not charset:
    charset = 'utf-8'

# Push our detected encoding to termitheme
# (otherwise it just assumes utf-8)
core.CHARSET = charset

argv = []
if sys.platform.startswith("win"):
    argv = core.win32_unicode_argv()
else:
    argv = [a.decode(charset) if isinstance(a, str) else a
            for a in sys.argv]

mode = usage
_cmds = commands.get_cmds()
_cmds['version'] = print_version

if len(argv) > 1 and argv[1] in _cmds:
    # Unwrap the onion....
    ctor = _cmds[argv[1]] # str  -> type
    handler = ctor()      # type -> instance
    mode = handler.run    # instance -> function [bound method]
    del argv[1:2] # consume argument

sys.exit(mode(argv))

