import locale
import os.path
import sys
from termitheme import core, commands, version

VERSION = version.version
if version.revision:
    VERSION += " [rev " + version.revision + "]"

def usage (argv, e=None):
    prog = os.path.basename(argv[0])
    if e:
        print "Error: %s" % e.args[0]
    else:
        print "Usage: %s <command> [command arguments...]" % prog
        print
        print "Available commands:"
        for cmd,handler_cls in commands.get_cmd_iter():
            handler = handler_cls()
            handler.show_usage(argv[0])
        print
        print "For help on a command, use %s <command> --help" % prog
        print
    return 2

class PrintVersion (commands.Command):
    cmdname = "version"
    usage_extended = ''
    def run (self, argv):
        if argv and len(argv) > 1:
            p = self.get_parser(argv[0])
            p.parse_args(['--help'])
        else:
            print "termitheme version %s" % VERSION
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

commands.register_cmd(PrintVersion)
_cmdnames = commands.get_cmd_names()

if len(argv) > 1 and argv[1] in _cmdnames:
    cmdname = argv[1]
    del argv[1:2] # consume argument
    try:
        rc = commands.run_cmd(cmdname, argv)
    except Exception, e:
        usage(argv, e)
        rc = 2
else:
    rc = usage(argv)

sys.exit(rc)

