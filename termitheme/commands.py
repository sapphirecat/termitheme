from __future__ import absolute_import, division, with_statement

import optparse
import os.path
import sys

from . import core

# argv[0] used if a command is called without argv
self_argv0 = __name__
_handlers = None

class _Command (object):
    cmdname = "command"
    usage_extended = "[command's options]"
    def parse_argv (self, argv):
        p = self.get_parser(argv[0])
        return p.parse_args(argv[1:])

    def get_parser (self, argv0=None):
        usage = '%%prog %s %s' % (self.cmdname, self.usage_extended)
        prog = os.path.basename(argv0)
        p = optparse.OptionParser(prog=prog, usage=usage)
        self._add_options(p)
        return p

    def show_usage (self, argv0=None, outfp=None):
        print "  %s %s" % (self.cmdname, self.usage_extended)

    def _add_options (self, *args):
        raise Exception("Method not implemented on subclass")

    def run (self, argv, *args, **kwargs):
        raise Exception("Method not implemented on subclass")


class Export (_Command):
    cmdname = "export"
    usage_extended = "[-c file] [-n name] [-t type] [-U] profile [filename]"
    def _add_options (self, p):
        t_help = ("Export from terminal type TYPE (available types: %s)" %
                  ", ".join(core.terminal.supported_types()))

        ao = p.add_option
        ao("-c", "--credits", dest="credits", metavar="FILE",
           help="Include contents of FILE as credits in the exported file")
        ao("-n", "--name", dest="name", metavar="NAME",
           help="Set the profile name to NAME in the exported file")
        ao("-t", "--terminal", dest="terminal", metavar="TYPE",
           default=core.terminal.default_type,
           help=t_help)
        ao("-U", "--utf-8", "--utf8", dest="utf8", action="store_true",
           help="Treat files as containing UTF-8 character data")

    def run (self, argv=None, profile=None, filename=None):
        if not (argv or profile):
            usage("Either argv or profile is required.")
        elif not argv:
            argv = ['<%s.cmd_export>' % self_argv0, profile]
            if filename:
                argv.append(filename)

        (opts, args) = self.parse_argv(argv)
        real_name = opts.name if opts.name else args[0]
        if len(args) < 1:
            usage("Missing profile name.")
        elif len(args) == 1:
            args.append("%s.zip" % real_name)
        elif len(args) > 2:
            usage("Too many arguments.")

        profile_name, filename = args

        if opts.utf8:
            core.CHARSET = 'utf-8'

        try:
            io = core.terminal.get_io(opts.terminal)
        except (KeyError, ValueError), e:
            p_err(e.args[0])
            return 2

        try:
            dst = io.read_profile(profile_name)
            dst.name = real_name
        except:
            p_err("The theme '%s' does not exist." % profile_name)
            return 1

        try:
            themefile = core.ThemeFile(filename)
            if opts.credits:
                themefile.set_credits(opts.credits)
            themefile.write(dst)
        except Exception, e:
            p_err("Failed to write theme to '%s':" % filename)
            p_err("\t%s" % e)
            return 1

        print "Exported theme '%s' as '%s' to %s." % (profile_name,
                                                      real_name,
                                                      filename)


class Import (_Command):
    cmdname = "import"
    usage_extended = "{-c | [-b profile] [-n name] [-o] [-t type]} filename"
    def _add_options (self, p):
        t_help = ("Import to terminal type TYPE (available types: %s)" %
                  ", ".join(core.terminal.supported_types()))

        ao = p.add_option
        ao("-b", "--base", dest="base", metavar="PROFILE",
           help="Base on PROFILE instead of the default profile")
        ao("-c", "--credits", dest="credits", action="store_true",
           help="Print theme credits and exit.")
        ao("-n", "--name", dest="name", metavar="NAME",
           help="Name the newly created profile NAME")
        ao("-o", "--overwrite", dest="overwrite", action="store_true",
           help="Allow overwriting/updating an existing profile")
        ao("-t", "--terminal", dest="terminal", metavar="TYPE",
           default=core.terminal.default_type,
           help=t_help)

    def run (self, argv=None, filename=None):
        if not (argv or filename):
            usage("A filename is required, either through argv or filename.")
        elif not argv:
            argv = ['<%s.cmd_import>' % self_argv0, filename]

        (opts, args) = self.parse_argv(argv)
        if args is None:
            usage("No filename given.")
        elif len(args) > 1:
            usage("Too many arguments.")
        else:
            filename = args[0]

        try:
            io = core.terminal.get_io(opts.terminal)
        except (KeyError, ValueError), e:
            p_err(e.args[0])
            sys.exit(2)

        try:
            themefile = core.ThemeFile(filename)
            src = themefile.read()
        except:
            p_err("Theme file %s does not seem to be valid." % filename)
            sys.exit(1)

        if opts.credits:
            try:
                c = themefile.get_credits()
                if c is None:
                    print "No credits are available for this theme."
                else:
                    print c.encode(sys.stdout.encoding or core.CHARSET,
                                   'xmlcharrefreplace')
                sys.exit(0)
            except Exception, e:
                p_err("Error reading credits: '%s'" % e.args[0])
                sys.exit(1)

        if not opts.base:
            dst = io.read_profile()
            base = "default profile"
        else:
            try:
                dst = io.read_profile(opts.base)
                base = opts.base
            except:
                p_err("The base theme %s does not exist." % opts.base)
                sys.exit(1)

        dst_name = opts.name if opts.name else src.name
        if io.profile_exists(dst_name) and not opts.overwrite:
            p_err("The theme '%s' exists and --overwrite was not given." %
                  dst_name)
            sys.exit(1)

        try:
            dst.update(src)
            dst.name = dst_name
        except Exception, e:
            p_err("Error copying theme into profile:")
            p_err("\t%s" % e)
            sys.exit(1)

        try:
            io.write_profile(dst)
        except Exception, e:
            p_err("Error writing new profile to storage:")
            p_err("\t%s" % e.args[0])
            sys.exit(1)

        print "Saved theme '%s' as '%s' (based on %s)" % (src.name,
                                                          dst.name,
                                                          base)

_handlers = {}

def run_cmd (cmd, *args):
    handler_ctor = _handlers[cmd]
    handler = handler_ctor()
    return handler.run(*args)

def get_cmds ():
    return _handlers.copy()

def register_cmd (handler):
    _handlers[handler.cmdname] = handler

register_cmd(Import)
register_cmd(Export)

