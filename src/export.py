# Usage: export.py <profile> [<themefile>]
# Exports a gnome-terminal profile as a theme file.

def parse_args (argv):
    p = optparse.OptionParser(prog=os.path.basename(argv[0]),
                              usage='%prog profile [filename]')
    return p.parse_args(argv[1:])

def main (argv=None, profile=None, filename=None):
    if not (argv or profile):
        usage("Either argv or profile is required.")
    elif not argv:
        argv = ['<export.py#main>', profile]
        if filename:
            argv.append(filename)

    (opts, args) = parse_args(argv)
    if len(args) < 1:
        usage("Missing profile name.")
    elif len(args) == 1:
        args.append("%s.zip" % args[0])
    elif len(args) > 2:
        usage("Too many arguments.")

    profile_name, filename = args

    io = GnomeTerminalIO()
    try:
        dst = io.read_profile(profile_name)
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

    print "Exported theme '%s' to %s." % (profile_name, filename)


if __name__ == '__main__':
    main(sys.argv)
    sys.exit(0)

