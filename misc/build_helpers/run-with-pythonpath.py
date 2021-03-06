# -*- python -*-
# you must invoke this with an explicit python, from the tree root

"""Run an arbitrary command with a PYTHONPATH that will include the Tahoe
code, including dependent libraries. Run this like:

 python misc/build_helpers/run-with-pythonpath.py python foo.py
"""

import os, sys, subprocess

# figure out where support/lib/pythonX.X/site-packages is
# add it to os.environ["PYTHONPATH"]
# spawn the child process


def pylibdir(prefixdir):
    pyver = "python%d.%d" % (sys.version_info[:2])
    if sys.platform == "win32":
        return os.path.join(prefixdir, "Lib", "site-packages")
    else:
        return os.path.join(prefixdir, "lib", pyver, "site-packages")

basedir = os.path.dirname(os.path.abspath(__file__))
supportlib = pylibdir(os.path.abspath("support"))

oldpp = os.environ.get("PYTHONPATH", "").split(os.pathsep)
if oldpp == [""]:
    # grr silly split() behavior
    oldpp = []
newpp = os.pathsep.join(oldpp + [supportlib,])
os.environ['PYTHONPATH'] = newpp

from twisted.python.procutils import which
cmd = sys.argv[1]
if cmd and cmd[0] not in "/~.":
    cmds = which(cmd)
    if not cmds:
        print >>sys.stderr, "'%s' not found on PATH" % (cmd,)
        sys.exit(-1)
    cmd = cmds[0]

os.execve(cmd, sys.argv[1:], os.environ)
