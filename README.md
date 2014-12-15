DEAD PROJECT ALERT
==================

This project died with Gnome 2.x.


OVERVIEW
========

termitheme is a command-line application to help share color schemes for
your terminals with the world.  Termitheme 1.5 supports gnome-terminal on
the Gnome desktop, and PuTTY on Windows.  Some features of gnome-terminal,
such as transparent or image backgrounds, are not supported and will be
copied unchanged from an existing profile.  Likewise, many PuTTY features
are not stored in the theme files, and will be copied from an existing PuTTY
configuration.


QUICK START
===========

	$ unzip termitheme-1.5.zip
	$ cd termitheme-1.5
	$ ./termitheme import samples/BlackRock.zip
	Saved theme 'BlackRock' as 'BlackRock' (based on Default)
	$ ./termitheme export -n Newspeak BlackRock
	Exported theme 'BlackRock' as 'Newspeak' to Newspeak.zip


REQUIREMENTS
============

	* Python 2, 2.5+ (Python 3.x is currently not supported)
	* Gnome: Python Gconf bindings
	* Windows: Windows-native Python executable--not Cygwin

Termitheme is designed to be self-contained, and run from any folder,
without requiring installation.  However, it does require Python 2.5 or a
later Python 2 release.  Python 3 is not supported at this time.  Gnome
additionally requires the Python gconf bindings.  These are available in the
python-gconf package for Debian, Ubuntu, and derivatives, or
gnome-python2-gconf in Fedora.  These packages may be installed by default
in your distribution.  The current compatibility goals are Ubuntu 8.04
through 10.04 (Hardy Heron to Lucid Lynx).  Termitheme 1.5 has also been
tested on Fedora 7 and 14, Debian 5.0/lenny, and Ubuntu 11.04/natty beta.

Cygwin is not supported due to character set problems.


NEW IN TERMITHEME 1.5
=====================

Installability
--------------

While termitheme can still be run directly from its unpacked directory, it
now includes a distutils-based setup.py file for supporting standard
installation, if desired.


Command Line Reorganization
---------------------------

The termitheme command line has been reorganized for greater sensibility and
extensibility.  The old import.py and export.py scripts have been moved into a
single script, and a new positional parameter goes _before_ any other options
to specify which subcommand to run.  In addition, the directory has been
rearranged for greater "instant runnability" under more recent Python
versions, so the typical way to run the main termitheme script without
installation has also changed.  More on that below, but for now, examples:

	**OLD:** ./import.py samples/BlackRock.zip
	**NEW:** ./termitheme import samples/BlackRock.zip

	**OLD:** ./export.py Default "Newspeak by Me.zip"
	**NEW:** ./termitheme export -w "Newspeak by Me.zip" Default

The new structure is designed to be compatible with `python .` and the
`python -m termitheme_lib` mechanisms in supported versions of python, as
well as allowing the intuitive and simple method of using `./termitheme` to
work on all versions.  Finally, when it's actually installed, bin/termitheme
can't try to `import termitheme`, or it will attempt to import _itself,_ so
the core library has been renamed to termitheme_lib.

Option Changes
--------------

* The optional zipfile name, previously given to export as a second positional
  argument, has been replaced by the `-w` option.  The old method is possible,
	but deprecated, and `-w` takes precedence if both are specified.
* export now accepts a `-o` option.
* export accepts a `-m VERSION` option to omit compatibility with termitheme
  versions less than VERSION in the exported theme file.

New Commands
------------

`version` simply displays the version.

	./termitheme version

`pack` reads a given theme file, in any version that termitheme supports,
rewrites it with sections for all termitheme versions, and writes the result
into a termitheme file.  In essence, `pack` allows you to compile themes by
hand.

	./termitheme pack theme.ini
	./termitheme pack -c myfile -w "Legacy Deco.zip" legacy-deco.ini


RUNNING
=======

Starting with version 1.2, termitheme is distributed as an all-inclusive zip
file, containing this README file; \_\_main\_\_.py, which can be used to execute
the project without installing; the installable bin/termitheme script and
termitheme module; and the all-important LICENSE file.

After extracting the zip file, open a terminal or command prompt and cd to
the newly created termitheme-VERSION folder.

Commands beginning with "python" are given for Gnome with a compatible
python version in the default path. You may need to precede the commands
shown with a specific version or full path, such as 'python2', 'python2.7',
or "C:\Python26\python". In that case, the first import example might
become:

	$ python2.7 termitheme import samples/BlackRock.zip

Or on Windows, using a Python 2.6 installation:

	$ C:\Python26\python termitheme import samples/BlackRock.zip 


Import Examples
---------------

To load a theme, use the import command and give it the theme file as the
argument:

	$ ./termitheme import samples/BlackRock.zip

You can import it under a different name with the --name (-n) option:

	$ ./termitheme import --name "Dark Heat" samples/BlackRock.zip

For settings not stored in the theme file, such as select-by-word characters
and compatibility options, import copies the settings from the default
profile. To use a different profile, use the --base (-b) option:

	$ ./termitheme import --base Minotaur samples/BlackRock.zip

If you already have a profile named BlackRock and you try to import a theme
named BlackRock, termitheme will keep the existing profile data by default.
If you wish to replace the profile with the data in the theme file, use the
--overwrite (-o) switch:

	$ ./termitheme import --overwrite samples/BlackRock.zip

Of course, all of these options may be combined. To load a theme from
BlackRock.zip, basing it on the Minotaur profile, naming it Dark Heat, and
possibly overwriting an existing Dark Heat theme:

	$ ./termitheme import -o -b Minotaur -n "Dark Heat" samples/BlackRock.zip

There is one other option: as of termitheme-1.2, theme files may contain
credits, which can be viewed with the --credits (-c) switch:

	$ ./termitheme import -c samples/BlackRock.zip

When -c is given, the theme credits are printed, and termitheme quits
instead of taking any action. The -c switch takes precedence over the other
options.


Export Examples
---------------

To export a theme, use the export command with a profile name:

	$ ./termitheme export Minotaur

The --write (-w) option allows for saving it to a specific file (but the theme
will still import under the name Minotaur by default):

	$ ./termitheme export -w Taurus.zip Minotaur

The theme name inside the exported file can be set with the --name (-n)
option. This will produce Taurus.zip:

	$ ./termitheme export -n Taurus Minotaur

Combining the previous two examples, to produce a theme named Taurus inside
Bullish.zip:

	$ ./termitheme export -n Taurus -w Bullish.zip Minotaur

To include a message to be printed with import -c, create a file
containing the credits information, and use the --credits (-c) option of
export to include it:

	$ ./termitheme export -c CREDITS Minotaur

This file should be in the encoding of your current locale on Unix, or the
ANSI code page on Windows.  The credits can also be in UTF-8 format; in that
case, use the --utf-8 (-U) switch to let the export command know:

	$ ./termitheme export -U -c CREDITS Minotaur

For more details on termitheme's character set handling, see the Character
Sets section of this document.


Pack Examples
-------------

If you construct a theme by hand, use the pack command and the INI file to
build the termitheme theme file:

	$ ./termitheme pack industrial.ini

Assuming that industrial.ini contains a theme name of "Industrial", this will
produce a file named "Industrial.zip".  Several options, notably credits,
filename to write, and forced Unicode mode can be specified exactly as they
can with export:

	$ ./termitheme pack -c CREDITS industrial.ini
	$ ./termitheme pack -w Industrial-beta1.zip industrial.ini
	$ ./termitheme pack -c CREDITS -U industrial.ini

In this case, -U also affects the theme file (industrial.ini in the example).


Character Sets
--------------

termitheme attempts to use the system locale or ANSI code page by default;
this means that it's supposed to just work, without mangling characters as
the theme file moves between systems.  If the system locale is not what is
desired, for instance if the credits file should contain Cyrillic characters
when a Western European locale is active, then termitheme provides the
option of interpreting the credits file as UTF-8 instead.

Because the command line is processed before the UTF-8 option can take
effect, the command line is always interpreted according to the current
locale on Unix.  Therefore, filenames on Unix must be readable or writable
in the current locale.

On Windows, the command line is fetched in Unicode format from the Win32
API, and Unicode names should always be used when reading or writing files.
In this case, the ANSI code page should not matter.

Cygwin's Python is not officially supported, since it never calls the
Unicode versions of the Windows API, and therefore files may exist on the
system which cannot be opened by Cygwin.


PROJECT PAGE
============

* Termitheme: http://www.sapphirepaw.org/termitheme/
* Theme gallery: http://www.sapphirepaw.org/termitheme/themes.php
* Development: http://github.com/sapphirecat/termitheme


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

