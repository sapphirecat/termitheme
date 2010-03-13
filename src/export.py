# Usage: export.py <profile> <themefile>
# Exports a gnome-terminal profile as a theme file.

# TODO: parse option string
# TODO: write gathered profile to a file

def main (argv=None):
    io = GnomeTerminalIO()
    src = io.read_profile()
    dst = TerminalProfile('Newspeak')
    dst.update(src)
    io.write_profile(dst)

if __name__ == '__main__':
    main(sys.argv)

