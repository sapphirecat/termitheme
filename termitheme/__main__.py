import locale
import sys
from termitheme import core, commands, version

VERSION = version.version

def usage (argv):
    print "TODO: Usage here"
    return 2

def print_version ():
    print >>sys.stderr, "termitheme version %s" % VERSION
    return 0

_cmds = {
    'export': commands.cmd_export,
    'import': commands.cmd_import,
    'version': print_version,
}

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
if len(argv) > 1 and argv[1] in _cmds:
    mode = _cmds[argv[1]]
    del argv[1:2] # consume argument

sys.exit(mode(argv))

