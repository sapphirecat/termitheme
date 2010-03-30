# Usage: import.py [-n/--name <profile>] [-b/--base <profile>] <themefile>
# Imports a theme in <themefile> as a new gnome-terminal profile. The theme
# name from the <themefile> can be overridden using the -n option; the theme
# will use settings from gnome-terminal's default theme for non-theme-related
# settings. This, too, can be overridden with the -b option.

def parse_args (argv):
    p = optparse.OptionParser(prog=os.path.basename(argv[0]),
                              usage='%prog [options] filename')

    t_help = ("Export from terminal type TYPE (available types: %s)" %
              ", ".join(terminal.supported_types()))

    p.add_option("-b", "--base", dest="base", metavar="PROFILE",
                 help="Base on PROFILE instead of the default profile")
    p.add_option("-n", "--name", dest="name", metavar="NAME",
                 help="Name the newly created profile NAME")
    p.add_option("-o", "--overwrite", dest="overwrite", action="store_true",
                 help="Allow overwriting/updating an existing profile")
    p.add_option("-t", "--terminal", dest="terminal", metavar="TYPE",
                 default=terminal.default_type,
                 help=t_help)

    return p.parse_args(argv[1:])

def main (argv=None, filename=None):
    if not (argv or filename):
        usage("A filename is required, either through argv or filename.")
    elif not argv:
        argv = ['<import.py#main>', filename]

    (opts, args) = parse_args(argv)
    if args is None:
        usage("No filename given.")
    elif len(args) > 1:
        usage("Too many arguments.")
    else:
        filename = args[0]

    try:
        io = terminal.get_io(opts.terminal)
    except (KeyError, ValueError), e:
        p_err(e.args[0])
        sys.exit(2)

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

    try:
        themefile = ThemeFile(filename)
        src = themefile.read()
    except:
        p_err("Theme file %s does not seem to be valid." % filename)
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
        p_err("Error writing new profile to gconf:")
        p_err("\t%s" % e)
        sys.exit(1)

    print "Saved theme '%s' as '%s' (based on %s)" % (src.name,
                                                      dst.name,
                                                      base)


if __name__ == '__main__':
    main(sys.argv)
    sys.exit(0)

