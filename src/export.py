# Usage: export.py <profile> [<themefile>]
# Exports a gnome-terminal profile as a theme file.

def parse_args (argv):
    p = optparse.OptionParser(prog=os.path.basename(argv[0]),
                              usage='%prog [options] profile [filename]')

    t_help = ("Export from terminal type TYPE (available types: %s)" %
              ", ".join(terminal.supported_types()))

    p.add_option("-n", "--name", dest="name", metavar="NAME",
                 help="Set the profile name to NAME in the exported file")
    p.add_option("-t", "--terminal", dest="terminal", metavar="TYPE",
                 default=terminal.default_type,
                 help=t_help)

    return p.parse_args(argv[1:])

def main (argv=None, profile=None, filename=None):
    if not (argv or profile):
        usage("Either argv or profile is required.")
    elif not argv:
        argv = ['<export.py#main>', profile]
        if filename:
            argv.append(filename)

    (opts, args) = parse_args(argv)
    real_name = opts.name if opts.name else args[0]
    if len(args) < 1:
        usage("Missing profile name.")
    elif len(args) == 1:
        args.append("%s.zip" % real_name)
    elif len(args) > 2:
        usage("Too many arguments.")

    profile_name, filename = args

    try:
        io = terminal.get_io(opts.terminal)
    except (KeyError, ValueError), e:
        p_err(e.args[0])
        sys.exit(2)

    try:
        dst = io.read_profile(profile_name)
        dst.name = real_name
    except:
        p_err("The theme '%s' does not exist." % profile_name)
        sys.exit(1)

    try:
        themefile = ThemeFile(filename)
        themefile.write(dst)
    except Exception, e:
        p_err("Failed to write theme to '%s':" % filename)
        p_err("\t%s" % e)
        sys.exit(1)

    print "Exported theme '%s' as '%s' to %s." % (profile_name,
                                                  real_name,
                                                  filename)


if __name__ == '__main__':
    main(sys.argv)
    sys.exit(0)

