#vim600:fdm=marker

import gconf
import sys

# -- gconf value boxing/unboxing -- {{{1
# (aka "the way it was meant to be in a dynamic language")
# You can use get_$TYPE if you know _a priori_ what type the key you're getting
# is. Otherwise gconf_unbox(client.get(...)) will do its best.

def _gconf_unbox_primitive (v):
    m = getattr(v, 'get_' + v.type.value_nick)
    return m()

def _gconf_box_primitive (v, gtype=None):
    # NOTE: order matters here, as bool < float < int! So if int is checked
    # first, all bool and float parameters are converted to int.
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

def gconf_unbox (v):
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

def gconf_box (v, is_pair=False):
    if is_pair:
        if len(v) != 2:
            raise ValueError("Pair value is not actually a pair of items.")
        gv = gconf.Value(gconf.VALUE_PAIR)
        gv.set_car(_gconf_box_primitive(v[0]))
        gv.set_cdr(_gconf_box_primitive(v[1]))
    elif isinstance(v, (list, tuple)):
        v0 = _gconf_box_primitive(v[0])
        gv = gconf.Value(gconf.VALUE_LIST)
        gv.set_list_type(v0.type)
        gv.set_list([_gconf_box_primitive(i, v0.type) for i in v])
    else:
        gv = _gconf_box_primitive(v)
    return gv
#}}}1


# -- gnome-terminal gconf value handling -- {{{1
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
    # FIXME: this has fallen out of use :-(
    THEME_KEYS = ['background_color',
                  'cursor_shape',
                  'font',
                  'foreground_color',
                  'palette',
                  'scroll_background',
                  'use_system_font',
                  'visible_name']
    # use_theme_colors: "Use colors from system theme"
    STD_KEYS = [('use_theme_colors', False)]

    def __init__ (self, gconf_client=None):
        # initialize gconf
        if gconf_client is None:
            c = gconf.client_get_default()
        else:
            c = gconf_client
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

    def profile_names (self):
        """Return a list of all defined profile names."""

        return self._path_of.keys()

    def read_profile (self, name=None):
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
        # Duplicate ALL gnome-terminal settings instead of letting "non-theme"
        # settings revert to their defaults.
        for e in c.all_entries(path[:-1]):
            k = self._relative_key(e.get_key())
            p[k] = gconf_unbox(e.get_value())
        return p

    def write_profile (self, profile):
        """Write the profile to gconf."""

        if profile.name in self._path_of:
            # Modiied profile: save into current path
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
        # FIXME: This has to properly interpret TerminalProfile
        for k, v in profile.items():
            # FIXME: "is not None" still relevant w/ c.all_entries()?
            if v is not None and not k.startswith("color"):
                c.set(path + k, gconf_box(v))
        c.set_string(path + 'palette', profile.palette)
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
#}}}1


# TODO: Theme file IO (and format)


# -- gnome-terminal profile data structure -- {{{1
# This is smarter than a dict for future support of PuTTY themes.

class TerminalProfile (dict):
    """Generic terminal theme."""

    # Keys that take special
    _propmap = {
        'palette': 'palette',
        'visible_name': 'name',
    }

    def __init__ (self, name):
        self._values = dict()
        self._name = name

    # -- properties -- {{{2
    def get_palette (self):
        """Gnome-terminal compatible palette handling.

        Automatically translates to/from the color<N> keys."""

        pal = [self._c48(self["color"+str(i)]) for i in range(16)]
        return ":".join(pal)

    def set_palette (self, v):
        colors = [self._c24(i) for i in v.split(":")]
        for i in range(16):
            self["color%d" % i] = colors[i]

    palette = property(get_palette, set_palette)

    # Hack: visible_name is 'the name', which is immutable
    def get_name (self):
        """Visible name of the profile. Immutable."""
        return self._name
    def set_name (self, ignored):
        pass
    name = property(get_name, set_name)

    #}}}2
    # -- private methods -- {{{2
    def _c24 (self, c48):
        """Convert a 48-bit color to the closest possible 24-bit color."""

        c48 = c48.lstrip('#')
        if len(c48) != 12:
            raise ValueError("48-bit color '%s' has unexpected length" % c48)
        c24 = []
        for b in range(3):
            byte = round(int(c48[4*b:4*b+4], 16)/256, 0)
            if byte > 255:
                byte = 255
            elif byte < 0:
                byte = 0
            c24.append(byte)
        return '#' + (''.join(["%02x" % i for i in c24]))

    def _c48 (self, c24):
        """Convert a 24-bit color to a 48-bit color."""

        c24 = c24.lstrip('#')
        if len(c24) != 6:
            raise ValueError("24-bit color '%s' has unexpected length" % c24)
        c48 = []
        for b in range(3):
            v = c24[2*b:2*b+2]
            c48.append(v + v)
        return '#' + (''.join(c48))

    #}}}2
    # -- public API -- {{{2
    def __str__ (self):
        return "<TerminalProfile %s>" % self.name

    def update (self, other):
        # Prevent activating the magical keys on update
        if not isinstance(other, TerminalProfile):
            raise TypeError("update() requires TerminalProfile argument")
        dict.update(self, other)

    def __getitem__ (self, k):
        if k in self._propmap:
            return getattr(self, self._propmap[k])
        else:
            return dict.__getitem__(self, k)

    def __setitem__ (self, k, v):
        if k in self._propmap:
            return setattr(self, self._propmap[k], v)
        else:
            return dict.__setitem__(self, k, v)

    def __delitem__ (self, k):
        if k not in self._propmap:
            dict.__delitem__(self, k)
        else:
            raise KeyError("Virtual key '%s' cannot be deleted." % k)
    #}}}2

#}}}1

