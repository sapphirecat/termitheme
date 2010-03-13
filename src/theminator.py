import gconf
import sys

# -- gconf value boxing/unboxing --
# (aka "the way it was meant to be in a dynamic language")
# You can use get_$TYPE if you know _a priori_ what type the key you're getting is.
# Otherwise gconf_unbox(client.get(...)) will do its best.

def _gconf_unbox_primitive (v):
    m = getattr(v, 'get_' + v.type.value_nick)
    return m()

def _gconf_box_primitive (v, gtype=None):
    if isinstance(v, basestring):
        gv = gconf.Value(gconf.VALUE_STRING)
    elif isinstance(v, int):
        gv = gconf.Value(gconf.VALUE_INT)
    elif isinstance(v, float):
        gv = gconf.Value(gconf.VALUE_FLOAT)
    elif isinstance(v, bool):
        gv = gconf.Value(gconf.VALUE_BOOL)
    else:
        raise TypeError("Invalid type for primitive GConfValue: %s" % type(v))

    if gtype and gv.type != gtype:
        raise TypeError("List type mismatch: %s is not %s" % (gv.type, gtype))

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
        return [gconf_unbox(v.get_car()), gconf_unbox(v.get_cdr())]
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


# -- gnome-terminal gconf value handling --

class GnomeTerminalGConf (object):
    APP_ROOT = '/apps/gnome-terminal'
    DEFAULT_NAME = APP_ROOT + '/global/default_profile'
    PROFILE_LIST = APP_ROOT + '/global/profile_list'
    PROFILE_ROOT = APP_ROOT + '/profiles'
    PROFILE_NAME = '/visible_name'
    # future: handle background_{darkness|image|type} as well
    # major problem: where to put the bg image when importing
    THEME_KEYS = ['background_color',
                  'cursor_shape',
                  'font',
                  'foreground_color',
                  'palette',
                  'scroll_background',
                  'use_system_font',
                  'visible_name']
    STD_KEYS = [('use_theme_colors', False)]

    def __init__ (self, gconf_client=None):
        # initialize gconf
        if gconf_client is None:
            c = gconf.client_get_default()
        else:
            c = gconf_client
        self._gconf = c
        # initialize visible-name => gconf-profile-root-path mapping
        path = {}
        for dir in c.get_list(self.PROFILE_LIST, gconf.VALUE_STRING):
            name = c.get_string(self.PROFILE_ROOT + '/' + dir + self.PROFILE_NAME)
            path[name] = self.PROFILE_ROOT + '/' + dir + '/'
        self._path_of = path
        # initialize misc. junk for extensibility
        self._profile_ctor = GnomeTerminalProfile

    def profile_names (self):
        return self._path_of.keys()

    def read_profile (self, name=None):
        if name is None:
            name = self._get_default_name()
        p = self._profile_ctor(name)

        if name not in self._path_of:
            raise KeyError("No profile named '%s' exists." % name)

        c = self._gconf
        path = self._path_of[name]

        if not c.dir_exists(path[:-1]):
            raise ValueError("Profile named '%s' has no gconf tree at %s." % (name,
                                                                              path))
        for k in self.THEME_KEYS:
            setattr(p, k, gconf_unbox(c.get(path + k)))
        return p

    def write_profile (self, profile):
        # NOTE: Don't write keys with value=None
        pass

    def _get_default_name (self):
        def_path = self._gconf.get_string(self.DEFAULT_NAME)
        tail = '/' + def_path + '/'
        for name, path in self._path_of.items():
            if path.endswith(tail):
                return name
        raise ValueError("Default name could not be found. Odd!")


# -- gnome-terminal profile data structure --
# although why this isn't just a dict... hmmmm

class GnomeTerminalProfile (object):
    def __init__ (self, name):
        self.name = name
    # TODO: Validation of values
    def __str__ (self):
        attrs = []
        for i in sorted(dir(self)):
            if not i.startswith('_'):
                attrs.append('%s=%s' % (i, str(getattr(self, i))))
        return "<GnomeTerminalProfile %s>" % (" ".join(attrs),)

