﻿============
Known issues
============

* `Overview`_
* `Issues in Tahoe-LAFS v1.8.0, released 2010-09-23`

  *  `Potential unauthorized access by JavaScript in unrelated files`_
  *  `Potential disclosure of file through embedded hyperlinks or JavaScript in that file`_
  *  `Command-line arguments are leaked to other local users`_
  *  `Capabilities may be leaked to web browser phishing filter / "safe browsing" servers`_
  *  `Known issues in the FTP and SFTP frontends`_

Overview
========

Below is a list of known issues in recent releases of Tahoe-LAFS, and how to
manage them.  The current version of this file can be found at

http://tahoe-lafs.org/source/tahoe-lafs/trunk/docs/known_issues.rst

If you've been using Tahoe-LAFS since v1.1 (released 2008-06-11) or if you're
just curious about what sort of mistakes we've made in the past, then you might
want to read the "historical known issues" document:

http://tahoe-lafs.org/source/tahoe-lafs/trunk/docs/historical/historical_known_issues.txt

Issues in Tahoe-LAFS v1.8.0, released 2010-09-23
================================================

Potential unauthorized access by JavaScript in unrelated files
--------------------------------------------------------------

If you view a file stored in Tahoe-LAFS through a web user interface,
JavaScript embedded in that file might be able to access other files or
directories stored in Tahoe-LAFS which you view through the same web
user interface.  Such a script would be able to send the contents of
those other files or directories to the author of the script, and if you
have the ability to modify the contents of those files or directories,
then that script could modify or delete those files or directories.

how to manage it
~~~~~~~~~~~~~~~~

For future versions of Tahoe-LAFS, we are considering ways to close off
this leakage of authority while preserving ease of use -- the discussion
of this issue is ticket `#615 <http://tahoe-lafs.org/trac/tahoe-lafs/ticket/615>`_.

For the present, either do not view files stored in Tahoe-LAFS through a
web user interface, or turn off JavaScript in your web browser before
doing so, or limit your viewing to files which you know don't contain
malicious JavaScript.


Potential disclosure of file through embedded hyperlinks or JavaScript in that file
-----------------------------------------------------------------------------------

If there is a file stored on a Tahoe-LAFS storage grid, and that file
gets downloaded and displayed in a web browser, then JavaScript or
hyperlinks within that file can leak the capability to that file to a
third party, which means that third party gets access to the file.

If there is JavaScript in the file, then it could deliberately leak
the capability to the file out to some remote listener.

If there are hyperlinks in the file, and they get followed, then
whichever server they point to receives the capability to the
file. Note that IMG tags are typically followed automatically by web
browsers, so being careful which hyperlinks you click on is not
sufficient to prevent this from happening.

how to manage it
~~~~~~~~~~~~~~~~

For future versions of Tahoe-LAFS, we are considering ways to close off
this leakage of authority while preserving ease of use -- the discussion
of this issue is ticket `#127 <http://tahoe-lafs.org/trac/tahoe-lafs/ticket/127>`_.

For the present, a good work-around is that if you want to store and
view a file on Tahoe-LAFS and you want that file to remain private, then
remove from that file any hyperlinks pointing to other people's servers
and remove any JavaScript unless you are sure that the JavaScript is not
written to maliciously leak access.


Command-line arguments are leaked to other local users
------------------------------------------------------

Remember that command-line arguments are visible to other users (through
the 'ps' command, or the windows Process Explorer tool), so if you are
using a Tahoe-LAFS node on a shared host, other users on that host will
be able to see (and copy) any caps that you pass as command-line
arguments.  This includes directory caps that you set up with the "tahoe
add-alias" command.

how to manage it
~~~~~~~~~~~~~~~~

As of Tahoe-LAFS v1.3.0 there is a "tahoe create-alias" command that does
the following technique for you.

Bypass add-alias and edit the NODEDIR/private/aliases file directly, by
adding a line like this:

  fun: URI:DIR2:ovjy4yhylqlfoqg2vcze36dhde:4d4f47qko2xm5g7osgo2yyidi5m4muyo2vjjy53q4vjju2u55mfa

By entering the dircap through the editor, the command-line arguments
are bypassed, and other users will not be able to see them. Once you've
added the alias, if you use that alias instead of a cap itself on the
command-line, then no secrets are passed through the command line.  Then
other processes on the system can still see your filenames and other
arguments you type there, but not the caps that Tahoe-LAFS uses to permit
access to your files and directories.


Capabilities may be leaked to web browser phishing filter / "safe browsing" servers
-----------------------------------------------------------------------------------

Firefox, Internet Explorer, and Chrome include a "phishing filter" or
"safe browing" component, which is turned on by default, and which sends
any URLs that it deems suspicious to a central server.

Microsoft gives a brief description of their filter's operation at
<http://blogs.msdn.com/ie/archive/2005/09/09/463204.aspx>. Firefox
and Chrome both use Google's "safe browsing API" which is documented
at <http://code.google.com/apis/safebrowsing/> and
<http://code.google.com/p/google-safe-browsing/wiki/Protocolv2Spec>.

This of course has implications for the privacy of general web browsing
(especially in the cases of Firefox and Chrome, which send your main
personally identifying Google cookie along with these requests without
your explicit consent, as described for Firefox in
<https://bugzilla.mozilla.org/show_bug.cgi?id=368255>).

The reason for documenting this issue here, though, is that when using the
Tahoe-LAFS web user interface, it could also affect confidentiality and integrity
by leaking capabilities to the filter server.

Since IE's filter sends URLs by SSL/TLS, the exposure of caps is limited to
the filter server operators (or anyone able to hack the filter server) rather
than to network eavesdroppers. The "safe browsing API" protocol used by
Firefox and Chrome, on the other hand, is *not* encrypted, although the
URL components are normally hashed.

Opera also has a similar facility that is disabled by default. A previous
version of this file stated that Firefox had abandoned their phishing
filter; this was incorrect.

how to manage it
~~~~~~~~~~~~~~~~

If you use any phishing filter or "safe browsing" feature, consider either
disabling it, or not using the WUI via that browser. Phishing filters have
very limited effectiveness (see
<http://lorrie.cranor.org/pubs/ndss-phish-tools-final.pdf>), and phishing
or malware attackers have learnt how to bypass them.

To disable the filter in IE7 or IE8:
````````````````````````````````````

- Click Internet Options from the Tools menu.

- Click the Advanced tab.

- If an "Enable SmartScreen Filter" option is present, uncheck it.
  If a "Use Phishing Filter" or "Phishing Filter" option is present,
  set it to Disable.

- Confirm (click OK or Yes) out of all dialogs.

If you have a version of IE that splits the settings between security
zones, do this for all zones.

To disable the filter in Firefox:
`````````````````````````````````

- Click Options from the Tools menu.

- Click the Security tab.

- Uncheck both the "Block reported attack sites" and "Block reported
  web forgeries" options.

- Click OK.

To disable the filter in Chrome:
````````````````````````````````

- Click Options from the Tools menu.

- Click the "Under the Hood" tab and find the "Privacy" section.

- Uncheck the "Enable phishing and malware protection" option.

- Click Close.


Known issues in the FTP and SFTP frontends
------------------------------------------

These are documented in docs/frontends/FTP-and-SFTP.txt and at
<http://tahoe-lafs.org/trac/tahoe-lafs/wiki/SftpFrontend>.


Traffic analysis based on sizes of files/directories, storage indices, and timing
---------------------------------------------------------------------------------

Files and directories stored by Tahoe-LAFS are encrypted, but the ciphertext
reveals the exact size of the original file or directory representation.
This information is available to passive eavesdroppers and to server operators.

For example, a large data set with known file sizes could probably be
identified with a high degree of confidence.

Uploads and downloads of the same file or directory can be linked by server
operators, even without making assumptions based on file size. Anyone who
knows the introducer furl for a grid may be able to act as a server operator.
This implies that if such an attacker knows which file/directory is being
accessed in a particular request (by some other form of surveillance, say),
then they can identify later or earlier accesses of the same file/directory.

Observing requests during a directory traversal (such as a deep-check
operation) could reveal information about the directory structure, i.e.
which files and subdirectories are linked from a given directory.

Attackers can combine the above information with inferences based on timing
correlations. For instance, two files that are accessed close together in
time are likely to be related even if they are not linked in the directory
structure. Also, users that access the same files may be related to each other.
