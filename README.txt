OVERVIEW
========

termitheme is a pair of scripts to help share color schemes for your
terminals with the world.  Termitheme 1.2 supports gnome-terminal on the
Gnome desktop, and PuTTY on Windows.  Some features of gnome-terminal, such
as transparent or image backgrounds, are not supported and will be copied
unchanged from an existing profile.  Likewise, many PuTTY features are not
stored in the theme files, and will be copied from an existing PuTTY
configuration.


QUICK START
===========

	$ unzip termitheme-1.2.zip
	$ cd termitheme-1.2
	$ ./import.py BlackRock.zip
	Saved theme 'BlackRock' as 'BlackRock' (based on Default)
	$ ./export.py -n Newspeak BlackRock
	Exported theme 'BlackRock' as 'Newspeak' to Newspeak.zip
	$

REQUIREMENTS
============

	* Python 2, 2.5+ (Python 3.x is currently not supported)
	* Gnome: Python Gconf bindings

Termitheme is designed to be self-contained, and run from any folder,
without requiring installation.  However, it does require Python 2.5 or a
later Python 2 release.  Python 3 is not supported at this time.  Gnome
additionally requires the Python gconf bindings.  These are available in the
python-gconf package for Debian, Ubuntu, and derivatives, or
gnome-python2-gconf in Fedora.  These packages may be installed by default
in your distribution.  The current compatibility goals are Ubuntu 8.04
through 10.04 (Hardy Heron to Lucid Lynx).  Termitheme 1.2 should be
compatible with Fedora Core 7 through 12 and Debian 5.0 (lenny) as well, but
these platforms have not been tested.


RUNNING
=======

Starting with version 1.2, termitheme is distributed as an all-inclusive zip
file, containing this README file; import.py and export.py scripts; the
components of the scripts in the src directory; and a Makefile for building
import.py and export.py from the sources.  After extracting the zip file,
open a terminal or command prompt and cd to the newly created termitheme-1.2
folder.

The commands below are given for Gnome with a compatible python version in
the default path. You may need to precede the commands shown with 'python2',
'python2.7', or "C:\Python26\python". E.g. the first import example would
become:

	$ python2.7 ./import.py BlackRock.zip

Or on Windows, using a Python 2.6 installation:

	$ C:\Python26\python ./import.py BlackRock.zip 


Import Examples
---------------

To load a theme, run import.py and give it the theme file as the argument:

	$ ./import.py BlackRock.zip

You can import it under a different name with the --name (-n) option:

	$ ./import.py --name "Dark Heat" BlackRock.zip

For settings not stored in the theme file, such as select-by-word characters
and compatibility options, import.py copies the settings from the default
profile. To use a different profile, use the --base (-b) option:

	$ ./import.py --base Minotaur BlackRock.zip

If you already have a profile named BlackRock and you try to import a theme
named BlackRock, termitheme will keep the existing profile data by default.
If you wish to replace the profile with the data in the theme file, use the
--overwrite (-o) switch:

	$ ./import.py --overwrite BlackRock.zip

Of course, all of these options may be combined. To load a theme from
BlackRock.zip, basing it on the Minotaur profile, naming it Dark Heat, and
possibly overwriting an existing Dark Heat theme:

	$ ./import.py -o -b Minotaur -n "Dark Heat" BlackRock.zip

There is one other option: as of termitheme-1.2, theme files may contain
credits, which can be viewed with the --credits (-c) switch:

	$ ./import.py -c BlackRock.zip

When -c is given, the theme credits are printed, and termitheme quits
instead of taking any action. The -c switch takes precedence over the other
options.


Export Examples
---------------

To export a theme, use export.py with a profile name:

	$ ./export.py Minotaur

A filename can follow the theme name, to save it to a specific file (but the
theme will still import under the name Minotaur by default):

	$ ./export.py Minotaur Taurus.zip

The theme name inside the exported file can be set with the --name (-n)
option. This will produce Taurus.zip:

	$ ./export.py -n Taurus Minotaur

Combining the previous two examples, to produce a theme named Taurus inside
Bullish.zip:

	$ ./export.py -n Taurus Minotaur Bullish.zip

To include a message to be printed with import.py -c, create a file
containing the credits information, and use the --credits (-c) option of
export.py to include it:

	$ ./export.py -c CREDITS Minotaur

(This file should be in the encoding of your current locale.  If you don't
know what this means, it is most likely that way by default.)


PROJECT PAGE
============

Termitheme: http://www.sapphirepaw.org/projects/termitheme.php
Theme gallery: http://www.sapphirepaw.org/projects/themes/


SUBMITTING THEMES TO THE GALLERY
================================

Send the following information to devel at sapphirepaw.org:

	* The theme file, as an attachment or link
	* The desired license, e.g. CC-BY-SA 3.0
	* Attribution name
	* Preview link, such as a screenshot or blog post (this must be
	  a link, as screenshots will not be hosted)

If any of this information is not included, then the theme cannot be
published.

