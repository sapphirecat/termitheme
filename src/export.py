# Usage: export.py <profile> <themefile>
# Exports a gnome-terminal profile as a theme file.

def main (argv=None):
    io = GnomeTerminalGConf()
    for n in io.profile_names():
        print io.read_profile(n)

if __name__ == '__main__':
    main(sys.argv)

