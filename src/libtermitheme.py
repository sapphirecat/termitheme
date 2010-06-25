#vim600:fdm=marker

# BATTERIES INCLUDED
from contextlib import contextmanager
import ConfigParser
import codecs
import datetime
import locale
import optparse
import os.path
import re
import StringIO # Python2.5 compatible hackery
import sys
import time
import zipfile

# PLATFORM SUPPORT
# Unfortunately, I don't see a way to detect whether these are available,
# short of importing the module whether we'll use them or not.
# TODO: Check into supporting PuTTY on Linux

try:
    import gconf
except ImportError:
    gconf = None

try:
    import _winreg
except ImportError:
    _winreg = None

# Post-import platform support
# Bust us out of 'C' locale
locale.setlocale(locale.LC_ALL, '')
CHARSETS = []
try:
    CHARSETS.append(locale.nl_langinfo(locale.CODESET))
except AttributeError: # win32! let's fake it.
    CHARSETS.append('mbcs')
# Fall back on UTF-8 as the West is headed that direction by default
if not CHARSETS or not re.match(r'utf-8$', CHARSETS[0], re.I):
    CHARSETS.append('utf-8')


#{{{ Character set conversion for command line etc.
def win32_unicode_argv():
    """Uses shell32.GetCommandLineArgvW to get sys.argv as a list of Unicode
    strings.

    Versions 2.x of Python don't support Unicode in sys.argv on
    Windows, with the underlying Windows API instead replacing multi-byte
    characters with '?'.

    This version's heritage (oldest first):
        http://code.activestate.com/recipes/572200/
        http://stackoverflow.com/questions/846850/

    This function has been snipped out so that no globals are written.
    """

    # ctypes included as of Python 2.5
    from ctypes import POINTER, byref, cdll, c_int, windll
    from ctypes.wintypes import LPCWSTR, LPWSTR

    GetCommandLineW = cdll.kernel32.GetCommandLineW
    GetCommandLineW.argtypes = []
    GetCommandLineW.restype = LPCWSTR

    CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
    CommandLineToArgvW.restype = POINTER(LPWSTR)

    cmd = GetCommandLineW()
    argc = c_int(0)
    argv = CommandLineToArgvW(cmd, byref(argc))
    if argc.value > 0:
        # Remove Python executable and commands if present
        start = argc.value - len(sys.argv)
        return [argv[i] for i in
                xrange(start, argc.value)]

##}}}


#{{{ Color conversion

class _ColorParser (object):
    def __init__ (self): #{{{
        def xdigits (len):
            return '([0-9a-f]{%d})' % len

        def decbyte ():
            return '(2(?:5[0-5]|[0-4][0-9])|1?[0-9]{1,2})'

        dec_core = [decbyte() for i in range(3)]
        dec_str = r',\s*'.join(dec_core)

        self._color_re = {
            '24': re.compile('^#?' + (3 * xdigits(2)) + '$', re.I),
            '48': re.compile('^#?' + (3 * xdigits(4)) + '$', re.I),
            '24dec': re.compile('^' + dec_str + '$'),
        }
    #}}}

    def parse24 (self, color): #{{{
        m = self._color_re['24'].match(color)
        if m is None:
            raise ValueError("Invalid 24-bit hex color '%s'" % color)
        return [self._double(int(h, 16)) for h in m.groups()]

    def to24 (self, color):
        if len(color) != 3:
            raise ValueError("Unexpected color length.")
        rgb = ''.join(["%02x" % (v//256,) for v in color])
        return '#' + rgb

    def is24 (self, v):
        if isinstance(v, basestring) and self._color_re['24'].match(v):
            return True
        return False
    #}}}

    def parse24dec (self, color): #{{{
        m = self._color_re['24dec'].match(color)
        if m is None:
            raise ValueError("Invalid 24-bit decimal color '%s'" % color)
        return [self._double(int(d, 10)) for d in m.groups()]

    def to24dec (self, color):
        if len(color) != 3:
            raise ValueError("Unexpected color length.")
        return ','.join(["%d" % (v//256,) for v in color])

    def is24dec (self, v):
        if isinstance(v, basestring) and self._color_re['24dec'].match(v):
            return True
        return False
    #}}}

    def parse48 (self, color): #{{{
        m = self._color_re['48'].match(color)
        if m is None:
            raise ValueError("Invalid 48-bit hex color '%s'" % color)
        return [int(h, 16) for h in m.groups()]

    def to48 (self, color):
        if len(color) != 3:
            raise ValueError("Unexpected color length.")
        rgb = ''.join(["%04x" % v for v in color])
        return '#' + rgb

    def is48 (self, v):
        if isinstance(v, basestring) and self._color_re['48'].match(v):
            return True
        return False
    #}}}

    def parsehex (self, color): #{{{
        if len(color) > 7:
            return self.parse48(color)
        else:
            return self.parse24(color)
    #}}}

    def is_color (self, v): #{{{
        if isinstance(v, list) and len(v) == 3:
            # test channel values
            return all([0 <= ch <= 65535 for ch in v])
        return False
    #}}}

    def _double (self, byteval): #{{{
        if 0 <= byteval <= 255:
            return byteval + byteval*256
        raise ValueError("Byte value out of range: %d" % byteval)
    #}}}

color = _ColorParser()

#}}}


#{{{ Theme file IO
#
# The file format is intentionally simple: a zip file containing a theme.ini
# file, whose keys/values are exactly what TerminalProfile is.
#
# theme.ini, of course, is just an INI file like so...
# [Termitheme1]
# key=value
# key=value
#
# This way, everything can be handled with zipfile and ConfigParser; and
# when we get to figuring out where to unpack a background-image, the image
# can be neatly added to the theme zip without changing the overall format.
#
# As such, this version is designed not to care about extra files in the zip
# archive.
#

class _ThemeFileVersion (object):
    # Keys are theme file keys (e.g. color0); values are a 4-tuple of
    # parser_func, marshaller_func/None, comment_func/None, type shorthand.
    # The type shorthand is only useful for upgrade_colors right now.
    _keytable = None
    _readonly = None
    _files = None
    _fns = None

    def __init__ (self, other=None):
        self._keytable = other._keytable.copy() if other else {}
        self._files = other._files.copy() if other else {}
        self._readonly = other._readonly.copy() if other else set()
        self._fns = {
            'c48': (color.parsehex, color.to48, self._comment_color),
            'c24': (color.parsehex, color.to24, self._comment_color),
            's': (self._parse_str, self._to_str, None),
            'u': (self._parse_unicode, self._to_unicode, None),
            'b': (self._parse_bool, self._to_bool, None),
        }

    def _add (self, iterable, typename):
        for k in iterable:
            self._keytable[k] = typename

    def set_readonly (self, iterable):
        for k in iterable:
            self._readonly.add(k)

    #{{{ add_DATATYPE methods
    def add_color48 (self, iterable):
        self._add(iterable, 'c48')

    def add_color24 (self, iterable):
        self._add(iterable, 'c24')

    def add_str (self, iterable):
        self._add(iterable, 's')

    def add_unicode (self, iterable):
        self._add(iterable, 'u')

    def add_bool (self, iterable):
        self._add(iterable, 'b')
    #}}}

    #{{{ Version 1.2 feature support
    def upgrade_colors (self):
        for k, v in self._keytable.items():
            if v == 'c24':
                self._keytable[k] = 'c48'

    def add_archive_files (self, mapping):
        self._files.update(mapping)

    def get_archive_file (self, file_key):
        return self._files[file_key]

    def has_archive_file (self, file_key):
        return file_key in self._files
    #}}}

    #{{{ Main parse/marshal/comment methods
    def has_key (self, k):
        return k in self._keytable

    def writable_key (self, k):
        if k in self._keytable and k not in self._readonly:
            return True
        return False

    def parse_value (self, k, v):
        typename = self._keytable[k]
        parse_fn = self._fns[typename][0]
        return parse_fn(v)

    def marshal_value (self, k, v):
        typename = self._keytable[k]
        marshal_fn = self._fns[typename][1]
        return marshal_fn(v)

    def comment_value (self, k, v):
        typename = self._keytable[k]
        comment_fn = self._fns[typename][2]
        if comment_fn:
            return '; %s\n' % comment_fn(v)
        return None

    def _comment_color (self, v):
        return color.to24dec(v)
    #}}}

    #{{{ Primitive value parsers/marshallers
    def _parse_bool (self, v):
        return v[0].upper().startswith("T")
    def _to_bool (self, v):
        return repr(bool(v))

    # v1.2+
    def _parse_unicode (self, v):
        return v.decode('utf-8', 'replace')
    def _to_unicode (self, v):
        return unicode(v).encode('utf-8')

    # v1.0-1.1 (legacy)
    def _parse_str (self, v):
        return v
    def _to_str (self, v):
        return str(v)
    #}}}


v1 = _ThemeFileVersion()
v1.add_color24(["color%d" % i for i in range(16)])
v1.add_color24("fgcolor bgcolor fgbold".split())
v1.add_str("name font cursor_shape".split())
v1.add_bool("allow_bold force_font use_fgbold".split())

v1_2 = _ThemeFileVersion(v1)
v1_2.upgrade_colors()
v1_2.add_color48("bgbold fgcursor bgcursor".split())
# overrides the str type in v1
v1_2.add_unicode("name font cursor_shape".split())

v1_2.add_archive_files(dict(credits="credits.txt"))

# Now that v1_2 has taken these as r/w, set them r/o for v1.
# This lets us read v1.1 themes and write v1.0 themes.
v1.set_readonly("fgbold use_fgbold".split())

_versions = [('1_2', v1_2), ('1', v1)]

del v1, v1_2


class ThemeFile (object):
    filename = None
    version = None

    def __init__ (self, filename, profile_class=None):
        self.filename = filename
        if not profile_class:
            profile_class = TerminalProfile
        self._profile_ctor = profile_class

        self._files = dict()

    def get_versions (self):
        return [x[0] for x in _versions]

    def has_version (self, ver):
        return any(True for x in _versions if x[0] == ver)

    def set_credits (self, src_filename): #{{{
        self._set_file('credits', src_filename)

    def get_credits (self):
        if 'credits' not in self._files:
            self._files['credits'] = self._get_file('credits')
        return self._files['credits']

    def _set_file (self, key, filename):
        with open(filename) as f:
            txt = f.read()
        self._files['credits'] = self._decode(txt, filename)

    def _get_file (self, key):
        try:
            zf = zipfile.ZipFile(self.filename, 'r')
        except:
            return None

        try:
            for ver, spec in _versions:
                if not spec.has_archive_file(key):
                    # Reached a version that precedes this feature
                    return None
                try:
                    s = zf.read(spec.get_archive_file(key))
                    return s.decode('utf-8', 'replace')
                except:
                    pass
        finally:
            zf.close()

        # All versions supported it, but it still wasn't found
        return None

    def _decode (self, txt, filename):
        for cset in CHARSETS:
            try:
                return txt.decode(cset, 'strict')
            except UnicodeError:
                pass
        # UnicodeDecodeError() takes 5 arguments (1 given)
        raise ValueError("Illegal characters in file '%s'" % filename)
    #}}}

    def read_open (self):
        """Return a ConfigParser associated with the theme file."""

        # Open zipfile and validate expected theme.ini file found
        zf = zipfile.ZipFile(self.filename, 'r') # can raise IOError
        # Python2.5 doesn't have ZipFile.open(), and ConfigParser doesn't
        # have any way to read directly from a string.
        fp = StringIO.StringIO(zf.read('theme.ini')) # can raise KeyError
        zf.close()

        cp = ConfigParser.RawConfigParser()
        cp.readfp(fp)
        return cp

    def read_profile (self, parser):
        """Populate a profile with the data from the parser."""

        profile_class = self._profile_ctor
        section = None
        for v in _versions:
            if parser.has_section('Termitheme' + v[0]):
                section = 'Termitheme' + v[0]
                marshaller = v[1]
                break

        if not section:
            raise KeyError("Theme file has no compatible theme version.")

        try:
            name = parser.get(section, 'name')
            p = profile_class(marshaller.parse_value('name', name))
        except ConfigParser.NoOptionError:
            raise KeyError("Theme file does not have a 'name' key.")

        for k, v in parser.items(section):
            if k == 'name': # special key
                continue
            try:
                p[k] = marshaller.parse_value(k, v)
            except KeyError:
                pass

        return p

    def read (self):
        """Read the theme file in self.filename and return a profile."""
        return self.read_profile(self.read_open())

    def write (self, profile):
        """Write the profile into self.filename."""

        data = '\n'.join([self._format_version(profile, ver, spec)
                          for ver, spec in _versions])
        spec = _versions[0][1]

        if os.path.exists(self.filename):
            raise ValueError("File '%s' exists." % self.filename)
        zf = zipfile.ZipFile(self.filename, 'w') # FIXME: binary/unicode
        zf.writestr(self._zipinfo('theme.ini'), data) # main theme
        for key, content in self._files.items(): # other archive files
            # These names I control, so they are always ASCII
            name = spec.get_archive_file(key)
            zf.writestr(self._zipinfo(name), content.encode('utf-8'))
        zf.close()

    def _format_version (self, profile, ver, m):
        lines = ["[Termitheme%s]\n" % ver, "name = %s\n" % profile.name]
        for k,v in sorted(profile.items()):
            if not m.writable_key(k):
                continue
            comment = m.comment_value(k, v)
            if comment:
                lines.append(comment)
            lines.append("%s = %s\n" % (k, m.marshal_value(k, v)))
        return ''.join(lines)

    def _zipinfo (self, filename):
        info = zipfile.ZipInfo()
        info.filename = filename
        # whoever designed this api is ridiculous
        now = datetime.datetime.fromtimestamp(time.time())
        info.date_time = (now.year, now.month, now.day,
                          now.hour, now.minute, now.second)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0644 << 16L # thank you bug 3394 (swarren)
        return info

#}}}


#{{{ Generic terminal profile data structure
# This is smarter than a dict for future support of PuTTY/Konsole themes.

class TerminalProfile (dict):
    """Generic terminal theme."""

    PROFILE_KEY_NAMES = ["color%d" % i for i in range(16)]
    PROFILE_KEY_NAMES.extend([
        # common (plus color0 through color15)
        'bgbold',
        'bgcolor',
        'bgcursor',
        'cursor_shape',
        'fgbold',
        'fgcolor',
        'fgcursor',
        'font',
        # gnome-terminal
        'force_font',
        'allow_bold',
        'use_fgbold',
        # PuTTY's cursor color, etc.? Konsole?
    ])

    name = None

    def __init__ (self, name):
        self._valid_keys = set(self.PROFILE_KEY_NAMES)
        self.name = name
        self._io_data = {}

    def is_valid_key (self, k):
        """Return True if k is a TerminalProfile key."""
        return k in self._valid_keys

    @contextmanager
    def ioslave (self, slave_name):
        """Give a reference to a slave-private dict to a block.
        
        Example: with profile.ioslave("konsole") as d: d['foo']='bar'"""
        if slave_name not in self._io_data:
            self._io_data[slave_name] = {}
        yield self._io_data[slave_name]

    #{{{ Dictionary interface
    def update (self, other):
        """Copy other's dictionary keys and ioslave data into self."""

        if not isinstance(other, TerminalProfile):
            raise TypeError("update requires a TerminalProfile")
        # Copy private data
        for k in other._io_data.keys():
            if k in self._io_data:
                self._io_data[k].update(other._io_data[k])
            else:
                self._io_data[k] = other._io_data[k]
        return dict.update(self, other)

    def __getitem__ (self, k):
        if k not in self._valid_keys:
            raise KeyError(self._bad_key(k))
        return dict.__getitem__(self, k)

    def __setitem__ (self, k, v):
        if k not in self._valid_keys:
            raise KeyError(self._bad_key(k))
        return dict.__setitem__(self, k, v)

    def __delitem__ (self, k):
        if k not in self._valid_keys:
            raise KeyError(self._bad_key(k))
        return dict.__delitem__(self, k)
    #}}}

    def __str__ (self):
        return "<TerminalProfile %s>" % self.name

    def _bad_key (self, k):
        return "Key '%s' is not a valid TerminalProfile key." % k

#}}}


#{{{ Terminal IO

#{{{ IO base class

class TerminalIOBase (object):
    def __init__ (self):
        self._profile_ctor = TerminalProfile

    def profile_names (self):
        raise NotImplementedError("TerminalIOBase#profile_names")

    def profile_exists (self, name):
        raise NotImplementedError("TerminalIOBase#profile_exists")

    def read_profile (self, name=None):
        raise NotImplementedError("TerminalIOBase#read_profile")

    def write_profile (self, profile):
        raise NotImplementedError("TerminalIOBase#write_profile")

#}}}


#{{{ GConf value boxing/unboxing
# (aka "the way it was meant to be in a dynamic language")
# You can use get_$TYPE if you know _a priori_ what type the key you're getting
# is. Otherwise gconf_unbox(client.get(...)) will do its best.
# Schema values are not supported because they're both weird and useless.

def _gconf_unbox_primitive (v): #{{{
    """Returns a Python value for the given gconf.Value.

    Raises TypeError if the value is not a primitive (bool/int/float/string)
    type."""

    try:
        m = getattr(v, 'get_' + v.type.value_nick)
        return m()
    except AttributeError:
        raise TypeError("GConf type is not primitive: %s" %
                        v.type.value_nick)
    #}}}

def _gconf_box_primitive (v, gtype=None): #{{{
    """Finds the gconf type and creates a gconf.Value for it.

    If gtype is present, it should be the type of a list, and the type of v
    MUST match gtype, otherwise TypeError is raised. TypeError is raised if
    the value is not a primitive (bool/int/float/string) gconf type."""

    # NOTE: order matters here, as bool < float < int! So if int is checked
    # first, all bool and float parameters are converted to int.
    # This may be a Python2-ism
    if isinstance(v, basestring):
        t = gconf.VALUE_STRING
    elif isinstance(v, bool):
        t = gconf.VALUE_BOOL
    elif isinstance(v, float):
        t = gconf.VALUE_FLOAT
    elif isinstance(v, int):
        # bounds check (handles 64-bit ints and int/long unification)
        if v >= 2**31 or v < -2**31:
            raise ValueError("Integer out of range for gconf")
        t = gconf.VALUE_INT
    else:
        raise TypeError("Invalid type for primitive GConfValue: %s" % type(v))

    if gtype and gv.type != gtype:
        raise TypeError("List type mismatch: %s is not %s" % (gv.type, gtype))

    gv = gconf.Value(t)
    m = getattr(gv, 'set_' + gv.type.value_nick)
    m(v)
    return gv
    #}}}

def gconf_unbox (v): #{{{
    """Convert any non-schema/non-invalid GConf type to a Python value.

    The unsupported types will be returned as None."""

    if v is None:
        return None
    nick = v.type.value_nick
    if nick == 'invalid' or nick == 'schema':
        return None
    elif nick == 'pair':
        return [_gconf_unbox_primitive(v.get_car()),
                _gconf_unbox_primitive(v.get_cdr())]
    elif nick == 'list':
        return [_gconf_unbox_primitive(i) for i in v.get_list()]
    else:
        return _gconf_unbox_primitive(v)
    #}}}

def gconf_box (v, is_pair=False): #{{{
    """Convert a Python value to a GConf value.

    If is_pair is True, a 2-element sequence will be set as a GConf pair.
    Otherwise, all list/tuple sequences become a list value. The GConf
    schema type is not supported."""

    if is_pair:
        if len(v) != 2:
            raise ValueError("Pair value is not actually a pair of items.")
        gv = gconf.Value(gconf.VALUE_PAIR)
        gv.set_car(_gconf_box_primitive(v[0]))
        gv.set_cdr(_gconf_box_primitive(v[1]))
    elif isinstance(v, (list, tuple)):
        # This boxes v[0] twice, but it is way easier.
        v0 = _gconf_box_primitive(v[0])
        gv = gconf.Value(gconf.VALUE_LIST)
        gv.set_list_type(v0.type)
        gv.set_list([_gconf_box_primitive(i, v0.type) for i in v])
    else:
        gv = _gconf_box_primitive(v)
    return gv
    #}}}
#}}}


#{{{ Gnome-terminal

class MockGConf (object):
    def set (self, k, v):
        self._print(k, gconf_unbox(v))
    def set_string (self, k, v):
        self._print(k, v)
    def set_bool (self, k, v):
        self._print(k, v)
    def set_float (self, k, v):
        self._print(k, v)
    def set_int (self, k, v):
        self._print(k, v)
    def _print (self, k, v):
        print "SET: %s = %s" % (k, repr(v))

class GnomeTerminalIO (TerminalIOBase):
    """GConf backend reader/writer for gnome-terminal."""

    APP_ROOT = '/apps/gnome-terminal'
    DEFAULT_NAME = APP_ROOT + '/global/default_profile'
    PROFILE_LIST = APP_ROOT + '/global/profile_list'
    PROFILE_ROOT = APP_ROOT + '/profiles'
    PROFILE_NAME = '/visible_name'
    # future: handle background_{darkness|image|type} as well
    # major problem: where to put the bg image when importing
    # value of None means "no translation" and is replaced in __init__
    THEME_KEYS = {'allow_bold': None,
                  'background_color': 'bgcolor',
                  'bold_color': 'fgbold',
                  'bold_color_same_as_fg': 'use_fgbold',
                  'cursor_shape': None,
                  'font': None,
                  'foreground_color': 'fgcolor',
                  'use_system_font': 'force_font'}
    REVERSE_BOOLS = set(['force_font', 'use_fgbold'])
    # use_theme_colors: "Use colors from system theme"
    STD_KEYS = [('use_theme_colors', False)]

    _slavename = 'gnome-terminal' # given to profile.ioslave(...)

    def __init__ (self, gconf_client=None): #{{{
        # initialize parent
        TerminalIOBase.__init__(self)

        # Translate None values in THEME_KEYS to actual values
        # Use list() to make sure we have a copy, not an iterator
        for k, v in list(self.THEME_KEYS.items()):
            if v is None:
                self.THEME_KEYS[k] = k

        # initialize gconf
        c = gconf_client if gconf_client else gconf.client_get_default()
        self._gconf = c

        # initialize visible-name => gconf-profile-root-path mapping
        # and record the maximum Profile## that we see
        path = {}
        max_prof = None
        for dir in c.get_list(self.PROFILE_LIST, gconf.VALUE_STRING):
            name = c.get_string(self.PROFILE_ROOT + '/' + dir +
                                self.PROFILE_NAME)
            path[name] = self.PROFILE_ROOT + '/' + dir + '/'
            if name.startswith("Profile"):
                if not max_prof or int(name[7:]) > max_prof:
                    max_prof = int(name[7:])
        self._path_of = path
        self._max_profile = max_prof if max_prof else -1
        #}}}

    def profile_names (self):
        """Return a list of all defined profile names."""
        return self._path_of.keys()

    def profile_exists (self, name):
        """Return whether the named profile exists."""
        return name in self._path_of

    def read_profile (self, name=None): # {{{
        """Read the given profile, or the default one if no name is given."""

        if name is None:
            name = self._get_default_name()
        p = self._profile_ctor(name)

        if name not in self._path_of:
            raise KeyError("No profile named '%s' exists." % name)

        c = self._gconf
        path = self._path_of[name]

        if not c.dir_exists(path[:-1]):
            raise ValueError("Profile named '%s' has no gconf tree at %s." %
                             (name, path))
        # Duplicate ALL gnome-terminal settings so that non-theme settings
        # won't revert to their defaults in write_profile.
        with p.ioslave(self._slavename) as private_data:
            theme = self.THEME_KEYS
            for e in c.all_entries(path[:-1]):
                k = self._relative_key(e.get_key())
                v = gconf_unbox(e.get_value())
                if color.is48(v):
                    v = color.parse48(v)
                elif k in self.REVERSE_BOOLS:
                    # fix up use_system_font vs. force_font, etc.
                    v = not v
                if k in theme:
                    p[theme[k]] = v
                else:
                    private_data[k] = v
            self._set_colors_from_palette(p, private_data['palette'])
            del private_data['palette']

        return p
        #}}}

    def write_profile (self, profile): #{{{
        """Write the profile to gconf."""

        c = self._gconf
        if profile.name in self._path_of:
            # Modified profile: save into current path
            path = self._path_of[profile.name]
            dir = path[:-1]
            save_path = False
        else:
            # New profile: get next unused profile number
            i = self._max_profile + 1
            dir = self.PROFILE_ROOT + '/Profile' + str(i)
            while c.dir_exists(dir):
                i += 1
                dir = self.PROFILE_ROOT + '/Profile' + str(i)
            save_path = True

        # Write all our keys to that profile dir
        path = dir + '/'
        #c=MockGConf()
        # Private keys (copied from default profile)
        with profile.ioslave(self._slavename) as private_data:
            for k, v in private_data.items():
                c.set(path + k, gconf_box(v))
        # Common theme keys
        for k, k_prof in self.THEME_KEYS.items():
            if k_prof in profile:
                val = profile[k_prof]
                if color.is_color(val):
                    val = color.to48(val)
                elif k in self.REVERSE_BOOLS:
                    val = not val
                c.set(path + k, gconf_box(val))
        # defaults for making the theme take hold (must overwrite ioslave)
        for k, v in self.STD_KEYS:
            c.set(path + k, gconf_box(v))
        # Special keys
        c.set_string(path + 'palette',
                     self._get_palette_from_profile(profile))
        c.set_string(path + 'visible_name', profile.name)

        if isinstance(c, MockGConf):
            return

        # Add the profile to the profile list
        if not save_path: # unless this was a modification
            return
        plst = c.get_list(self.PROFILE_LIST, gconf.VALUE_STRING)
        base_dir = self._relative_key(dir)
        if base_dir not in plst:
            plst.append(base_dir)
            c.set_list(self.PROFILE_LIST, gconf.VALUE_STRING, plst)
        #}}}

    #{{{ Internal interfaces
    def _relative_key (self, abs_key):
        base_pos = abs_key.rfind('/') + 1
        return abs_key[base_pos:]

    def _get_default_name (self):
        def_path = self._gconf.get_string(self.DEFAULT_NAME)
        if def_path is None:
            raise ValueError("Default name not found at %s." %
                             self.DEFAULT_NAME)
        tail = '/' + def_path + '/'
        for name, path in self._path_of.items():
            if path.endswith(tail):
                return name
        raise ValueError("Default name does not have a path mapping.")

    def _set_colors_from_palette (self, profile, palette):
        colors = [color.parse48(i) for i in palette.split(":")]
        if len(colors) < 16:
            raise ValueError("Palette does not contain enough colors.")
        for i in range(16):
            profile["color%d" % i] = colors[i]

    def _get_palette_from_profile (self, profile):
        pal = [color.to48(profile["color%d" % i]) for i in range(16)]
        return ":".join(pal)
    #}}}

#}}}


#{{{ PuTTY + Windows registry

class PuttyWinIO (TerminalIOBase):
    SESSIONS_DIR = r'Software\SimonTatham\PuTTY\Sessions'
    THEME_KEYS = {'Colour0': ('fgcolor',),
                  'Colour1': ('fgbold',),
                  'Colour2': ('bgcolor',),
                  'Colour3': ('bgbold',),
                  'Colour4': ('fgcursor',),
                  'Colour5': ('bgcursor',),
                  'Colour6': ('color0',),
                  'Colour7': ('color8',),
                  'Colour8': ('color1',),
                  'Colour9': ('color9',),
                  'Colour10': ('color2',),
                  'Colour11': ('color10',),
                  'Colour12': ('color3',),
                  'Colour13': ('color11',),
                  'Colour14': ('color4',),
                  'Colour15': ('color12',),
                  'Colour16': ('color5',),
                  'Colour17': ('color13',),
                  'Colour18': ('color6',),
                  'Colour19': ('color14',),
                  'Colour20': ('color7',),
                  'Colour21': ('color15',),
                  'Font': ('font', 'string'),
                 }
    STD_KEYS = [('UseSystemColours', False, 'bool_int'),
                ('BoldAsColour', True, 'bool_int')]
    for k in THEME_KEYS.keys():
        if k.startswith("Colour"):
            THEME_KEYS[k] = (THEME_KEYS[k][0], 'color')

    _slavename = 'putty-win'

    def __init__ (self):
        # initialize parent
        TerminalIOBase.__init__(self)

        if not _winreg:
            raise RuntimeError("Windows registry not available.")

        self._HIVE = _winreg.HKEY_CURRENT_USER
        self._theme_types = {
            'bool_int': (bool, int, _winreg.REG_DWORD),
            'color': (color.parse24dec, color.to24dec, _winreg.REG_SZ),
            'string': (None, None, _winreg.REG_SZ),
        }

    def profile_names (self):
        return self._winreg_map(_winreg.EnumKey,
                                self.SESSIONS_DIR)

    def profile_exists (self, name):
        try:
            _winreg.OpenKey(self._HIVE, self._session_key(name))
            return True
        except WindowsError: # XXX: test - does missing key cause this?
            return False

    def read_profile (self, name=None): #{{{
        p = self._profile_ctor(name)
        if name is None:
            return p

        try:
            values = self._winreg_map(_winreg.EnumValue,
                                      self._session_key(name))
        except WindowsError:
            raise KeyError("No profile named '%s' exists." % name)

        with p.ioslave(self._slavename) as private_data:
            theme = self.THEME_KEYS
            for k, v, t in values:
                if k in theme:
                    read_fn = self._theme_types[ theme[k][1] ][0]
                    if read_fn:
                        v = read_fn(v)
                    p[theme[k][0]] = v
                else:
                    private_data[k] = (v, t)
        return p
    #}}}

    def write_profile (self, profile): #{{{
        try:
            key = _winreg.CreateKey(self._HIVE,
                                    self._session_key(profile.name))

            try:
                # Private keys copied from base profile
                with profile.ioslave(self._slavename) as private_data:
                    for k, (v, t) in private_data.items():
                        _winreg.SetValueEx(key, k, 0, t, v)
                # Theme keys
                for putty_key, (t_key, typename) in self.THEME_KEYS.items():
                    if t_key in profile:
                        t, v = self._reg_serial(typename, profile[t_key])
                        _winreg.SetValueEx(key, putty_key, 0, t, v)
                # Defaults for making the theme take hold
                for k, v, t_name in self.STD_KEYS:
                    t, v = self._reg_serial(t_name, v)
                    _winreg.SetValueEx(key, k, 0, t, v)
                # No special keys for PuTTY/win
            finally:
                key.Close()

        except WindowsError, e:
            raise RuntimeError("Registry error writing profile '%s'" %
                               profile.name)

    #}}}

    def _session_key (self, name):
        return self.SESSIONS_DIR + '\\' + self._unicode_name(name)

    def _unicode_name (self, name):
        for cset in try_csets:
            try:
                uni_name = name.decode(cset, 'strict')
            except UnicodeError:
                pass

    def _reg_serial (self, typename, value):
        m, t = self._theme_types[typename][1:3]
        v = m(value) if m else value
        return (t, v)

    def _putty_name (self, raw_name):
        # encoding based on examination of WINDOWS/WINSTORE.C mungestr()
        always_encode = ' \\*?%.'
        dot_ok = False
        out = []
        hex_encode = codecs.getencoder('hex_codec')
        for c in raw_name:
            printable = ord(' ') <= ord(c) <= ord('~')
            if c in always_encode or not printable:
                out.append("%" + hex_encode(c)[0])
            else:
                out.append(c)
            if not dot_ok:
                dot_ok = True
                always_encode = always_encode.rstrip('.')
        return ''.join(out)


    def _winreg_map (self, winreg_method, key): #{{{
        rv = []
        h = _winreg.OpenKey(self._HIVE, key)
        try:
            i = 0
            while True:
                x = winreg_method(h, i)
                rv.append(x)
                i += 1
        except WindowsError:
            pass
        finally:
            h.Close()
        return rv
    #}}}
#}}}

#}}}


#{{{ Terminal switching code


class _TerminalTypes (dict):
    def _set_io (self, termname, io_class, set_default=False):
        self[termname] = io_class
        if set_default:
            self.default_type = termname

    def supports (self, termname):
        """Return whether a terminal is supported on the current platform."""

        return (termname in self and self[termname] is not None)

    def supported_types (self):
        """Return terminals actually supported on the current platform."""

        return sorted([k for k, v in self.items() if v])

    def get_io (self, termname, wrapper=None):
        """Get the IO class corresponding to termname.

        If wrapper is provided, it should be a function accepting the class,
        and returning a TerminalIO object."""

        if termname not in self:
            raise KeyError("Unknown terminal type: '%s'" % termname)
        elif not self[termname]:
            raise ValueError("Terminal type is not supported on this " +
                             "platform.")

        ctor = self[termname]
        if wrapper:
            return wrapper(ctor)
        else:
            return ctor()

terminal = _TerminalTypes(dict(gnome=None, putty=None))
if gconf:
    terminal._set_io('gnome', GnomeTerminalIO, True)
if _winreg:
    terminal._set_io('putty', PuttyWinIO, True)

#}}}


#{{{ Shared handling helpers for import/export scripts

def p_err (str):
    print >>sys.stderr, str

def usage (error_msg):
    p_err(error_msg)
    p_err("Use --help for details.")
    sys.exit(2)

#}}}

