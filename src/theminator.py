#vim600:fdm=marker

# Remaining plan is this...
# get on to real import/export, then putty! and konsole! and world
# domination!

from contextlib import contextmanager
import gconf
import re
import sys

#{{{1 GConf value boxing/unboxing
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
#}}}1


#{{{1 Color conversion

_c24_re = re.compile('^#?' + (3 * '([0-9a-f]{2})') + '$', re.I)
_c48_re = re.compile('^#?' + (3 * '([0-9a-f]{4})') + '$', re.I)

def color24 (c48): #{{{
    """Convert a 48-bit color to the closest possible 24-bit color."""

    m = _c48_re.match(c48)
    if m is None:
        raise ValueError("Invalid 48-bit color '%s'" % c48)
    c24 = '#'
    for hexval in m.groups():
        byte = round(int(hexval, 16)/256, 0)
        if byte > 255:
            byte = 255
        elif byte < 0:
            byte = 0
        c24 += '%02x' % byte
    return c24
    #}}}

def color48 (c24): #{{{
    """Convert a 24-bit color to a 48-bit color."""

    c24 = c24.lstrip('#')
    if len(c24) != 6:
        raise ValueError("24-bit color '%s' has unexpected length" % c24)
    c48 = []
    for b in range(3):
        v = c24[2*b:2*b+2]
        c48.append(v + v)
    return '#' + (''.join(c48))
    #}}}

#}}}1


#{{{1 Gnome-terminal GConf value handling
# Possible future directions: PuttyIO, KonsoleIO

class MockGConf (object):
    def set (self, k, v):
        self._print(k, gconf_unbox(v))
    def set_string (self, k, v):
        self._print(k, v)
    def _print (self, k, v):
        print "SET: %s = %s" % (k, repr(v))

class GnomeTerminalIO (object):
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
                  'cursor_shape': None,
                  'font': None,
                  'foreground_color': 'fgcolor',
                  'use_system_font': 'force_font'}
    # use_theme_colors: "Use colors from system theme"
    STD_KEYS = [('use_theme_colors', False)]

    _slavename = 'gnome-terminal' # given to profile.ioslave(...)

    def __init__ (self, gconf_client=None): #{{{
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

        # initialize misc. junk for extensibility
        self._profile_ctor = TerminalProfile
        #}}}

    def profile_names (self):
        """Return a list of all defined profile names."""
        return self._path_of.keys()

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
                if k in theme:
                    p[theme[k]] = v
                else:
                    private_data[k] = v
            self._set_colors_from_palette(p, private_data['palette'])
        return p
        #}}}

    def write_profile (self, profile): #{{{
        """Write the profile to gconf."""

        if profile.name in self._path_of:
            # Modified profile: save into current path
            path = self._path_of[name]
            dir = path[:-1]
            save_path = False
        else:
            # New profile: get next unused profile number
            c = self._gconf
            i = self._max_profile + 1
            dir = self.PROFILE_ROOT + '/Profile' + str(i)
            while c.dir_exists(dir):
                i += 1
                dir = self.PROFILE_ROOT + '/Profile' + str(i)
            save_path = True

        # Write all our keys to that profile dir
        path = dir + '/'
        #c=MockGConf()
        for k, v in self.STD_KEYS: # defaults for making the theme take hold
            c.set(path + k, gconf_box(v))
        # Common theme keys
        for k, k_prof in self.THEME_KEYS.items():
            if k_prof in profile:
                c.set(path + k, gconf_box(profile[k_prof]))
        # Private keys (copied from default profile)
        with profile.ioslave(self._slavename) as private_data:
            for k, v in private_data.items():
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
        colors = [color24(i) for i in palette.split(":")]
        if len(colors) < 16:
            raise ValueError("Palette does not contain enough colors.")
        for i in range(16):
            profile["color%d" % i] = colors[i]

    def _get_palette_from_profile (self, profile):
        pal = [color48(profile["color%d" % i]) for i in range(16)]
        return ":".join(pal)
    #}}}

#}}}1


#{{{1 TODO: Theme file IO (and format)
#}}}


#{{{1 Generic terminal profile data structure
# This is smarter than a dict for future support of PuTTY/Konsole themes.

class TerminalProfile (dict):
    """Generic terminal theme."""

    PROFILE_KEY_NAMES = ["color%d" % i for i in range(16)]
    PROFILE_KEY_NAMES.extend([
        # common (plus color0 through color15)
        'bgcolor',
        'cursor_shape',
        'font',
        'fgcolor',
        # gnome-terminal
        'force_font',
        'allow_bold',
        # PuTTY's cursor color, etc.? Konsole?
    ])

    def __init__ (self, name):
        self._valid_keys = set(self.PROFILE_KEY_NAMES)
        self._name = name
        self._io_data = {}

    @property
    def name (self):
        """Visible name of the profile. Immutable."""
        return self._name

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

#}}}1

