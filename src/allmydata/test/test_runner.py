# -*- coding: utf-8 -*-

from twisted.trial import unittest

from twisted.python import usage, runtime
from twisted.internet import utils
import os.path, re, sys
from cStringIO import StringIO
from allmydata.util import fileutil, pollmixin
from allmydata.util.encodingutil import unicode_to_argv, unicode_to_output, get_filesystem_encoding
from allmydata.scripts import runner

from allmydata.test import common_util
import allmydata

timeout = 240

srcfile = allmydata.__file__
srcdir = os.path.dirname(os.path.dirname(os.path.normcase(os.path.realpath(srcfile))))

rootdir = os.path.dirname(srcdir)
if os.path.basename(srcdir) == 'site-packages':
    if re.search(r'python.+\..+', os.path.basename(rootdir)):
        rootdir = os.path.dirname(rootdir)
    rootdir = os.path.dirname(rootdir)

bintahoe = os.path.join(rootdir, 'bin', 'tahoe')
if sys.platform == "win32":
    bintahoe += ".pyscript"
    if not os.path.exists(bintahoe):
       alt_bintahoe = os.path.join(rootdir, 'Scripts', 'tahoe.pyscript')
       if os.path.exists(alt_bintahoe):
           bintahoe = alt_bintahoe


class SkipMixin:
    def skip_if_cannot_run_bintahoe(self):
        if "cygwin" in sys.platform.lower():
            raise unittest.SkipTest("We don't know how to make this test work on cygwin: spawnProcess seems to hang forever. We don't know if 'bin/tahoe start' can be run on cygwin.")
        if not os.path.exists(bintahoe):
            raise unittest.SkipTest("The bin/tahoe script isn't to be found in the expected location (%s), and I don't want to test a 'tahoe' executable that I find somewhere else, in case it isn't the right executable for this version of Tahoe. Perhaps running 'setup.py build' again will help." % (bintahoe,))

    def skip_if_cannot_daemonize(self):
        self.skip_if_cannot_run_bintahoe()
        if runtime.platformType == "win32":
            # twistd on windows doesn't daemonize. cygwin should work normally.
            raise unittest.SkipTest("twistd does not fork under windows")


class BinTahoe(common_util.SignalMixin, unittest.TestCase, SkipMixin):
    def test_the_right_code(self):
        cwd = os.path.normcase(os.path.realpath("."))
        root_from_cwd = os.path.dirname(cwd)

        same = (root_from_cwd == rootdir)
        if not same:
            try:
                same = os.path.samefile(root_from_cwd, rootdir)
            except AttributeError, e:
                e  # hush pyflakes

        if not same:
            msg = ("We seem to be testing the code at %r,\n"
                   "(according to the source filename %r),\n"
                   "but expected to be testing the code at %r.\n"
                   % (rootdir, srcfile, root_from_cwd))
            if (not isinstance(cwd, unicode) and
                cwd.decode(get_filesystem_encoding(), 'replace') != os.path.normcase(os.path.realpath(os.getcwdu()))):
                msg += ("However, this may be a false alarm because the current directory path\n"
                        "is not representable in the filesystem encoding. Please run the tests\n"
                        "from the root of the Tahoe-LAFS distribution at a non-Unicode path.")
                raise unittest.SkipTest(msg)
            else:
                msg += "Please run the tests from the root of the Tahoe-LAFS distribution."
                self.fail(msg)

    def test_path(self):
        self.skip_if_cannot_run_bintahoe()
        d = utils.getProcessOutputAndValue(bintahoe, args=["--version-and-path"], env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 0, str(res))

            # Fail unless the allmydata-tahoe package is *this* version *and*
            # was loaded from *this* source directory.

            verstr = str(allmydata.__version__)

            self.failIfEqual(verstr, "unknown",
                             "We don't know our version, because this distribution didn't come "
                             "with a _version.py and 'setup.py darcsver' hasn't been run.")

            # The Python "rational version numbering" convention
            # disallows "-r$REV" but allows ".post$REV"
            # instead. Eventually we'll probably move to that. When we
            # do, this test won't go red:

            ix = verstr.rfind('-r')
            if ix != -1:
                altverstr = verstr[:ix] + '.post' + verstr[ix+2:]
            else:
                ix = verstr.rfind('.post')
                if ix != -1:
                    altverstr = verstr[:ix] + '-r' + verstr[ix+5:]
                else:
                    altverstr = verstr

            required_ver_and_path = "%s: %s (%s)" % (allmydata.__appname__, verstr, srcdir)
            alt_required_ver_and_path = "%s: %s (%s)" % (allmydata.__appname__, altverstr, srcdir)

            self.failUnless(out.startswith(required_ver_and_path) or out.startswith(alt_required_ver_and_path), (out, err, rc_or_sig, required_ver_and_path))
        d.addCallback(_cb)
        return d

    def test_unicode_arguments_and_output(self):
        self.skip_if_cannot_run_bintahoe()

        tricky = u"\u2621"
        try:
            tricky_arg = unicode_to_argv(tricky, mangle=True)
            tricky_out = unicode_to_output(tricky)
        except UnicodeEncodeError:
            raise unittest.SkipTest("A non-ASCII argument/output could not be encoded on this platform.")

        d = utils.getProcessOutputAndValue(bintahoe, args=[tricky_arg], env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 1, str(res))
            self.failUnlessIn("Unknown command: "+tricky_out, out)
        d.addCallback(_cb)
        return d

    def test_run_with_python_options(self):
        self.skip_if_cannot_run_bintahoe()

        # -t is a harmless option that warns about tabs.
        d = utils.getProcessOutputAndValue(sys.executable, args=['-t', bintahoe, '--version'],
                                           env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 0, str(res))
            self.failUnless(out.startswith(allmydata.__appname__+':'), str(res))
        d.addCallback(_cb)
        return d

    def test_version_no_noise(self):
        self.skip_if_cannot_run_bintahoe()
        import pkg_resources
        try:
            pkg_resources.require("Twisted>=9.0.0")
        except pkg_resources.VersionConflict:
            raise unittest.SkipTest("We pass this test only with Twisted >= v9.0.0")

        d = utils.getProcessOutputAndValue(bintahoe, args=["--version"], env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 0, str(res))
            self.failUnless(out.startswith(allmydata.__appname__+':'), str(res))
            self.failIfIn("DeprecationWarning", out, str(res))
            self.failUnlessEqual(err, "", str(res))
        d.addCallback(_cb)
        return d


class CreateNode(unittest.TestCase):
    # exercise "tahoe create-node", create-introducer,
    # create-key-generator, and create-stats-gatherer, by calling the
    # corresponding code as a subroutine.

    def workdir(self, name):
        basedir = os.path.join("test_runner", "CreateNode", name)
        fileutil.make_dirs(basedir)
        return basedir

    def run_tahoe(self, argv):
        out,err = StringIO(), StringIO()
        rc = runner.runner(argv, stdout=out, stderr=err)
        return rc, out.getvalue(), err.getvalue()

    def do_create(self, kind):
        basedir = self.workdir("test_" + kind)
        command = "create-" + kind
        is_client = kind in ("node", "client")
        tac = is_client and "tahoe-client.tac" or ("tahoe-" + kind + ".tac")

        n1 = os.path.join(basedir, command + "-n1")
        argv = ["--quiet", command, "--basedir", n1]
        rc, out, err = self.run_tahoe(argv)
        self.failUnlessEqual(err, "")
        self.failUnlessEqual(out, "")
        self.failUnlessEqual(rc, 0)
        self.failUnless(os.path.exists(n1))
        self.failUnless(os.path.exists(os.path.join(n1, tac)))

        if is_client:
            # tahoe.cfg should exist, and should have storage enabled for
            # 'create-node', and disabled for 'create-client'.
            tahoe_cfg = os.path.join(n1, "tahoe.cfg")
            self.failUnless(os.path.exists(tahoe_cfg))
            content = open(tahoe_cfg).read()
            if kind == "client":
                self.failUnless("\n[storage]\nenabled = false\n" in content)
            else:
                self.failUnless("\n[storage]\nenabled = true\n" in content)

        # creating the node a second time should be rejected
        rc, out, err = self.run_tahoe(argv)
        self.failIfEqual(rc, 0, str((out, err, rc)))
        self.failUnlessEqual(out, "")
        self.failUnless("is not empty." in err)

        # Fail if there is a non-empty line that doesn't end with a
        # punctuation mark.
        for line in err.splitlines():
            self.failIf(re.search("[\S][^\.!?]$", line), (line,))

        # test that the non --basedir form works too
        n2 = os.path.join(basedir, command + "-n2")
        argv = ["--quiet", command, n2]
        rc, out, err = self.run_tahoe(argv)
        self.failUnlessEqual(err, "")
        self.failUnlessEqual(out, "")
        self.failUnlessEqual(rc, 0)
        self.failUnless(os.path.exists(n2))
        self.failUnless(os.path.exists(os.path.join(n2, tac)))

        # test the --node-directory form
        n3 = os.path.join(basedir, command + "-n3")
        argv = ["--quiet", command, "--node-directory", n3]
        rc, out, err = self.run_tahoe(argv)
        self.failUnlessEqual(err, "")
        self.failUnlessEqual(out, "")
        self.failUnlessEqual(rc, 0)
        self.failUnless(os.path.exists(n3))
        self.failUnless(os.path.exists(os.path.join(n3, tac)))

        # test the --multiple form
        n4 = os.path.join(basedir, command + "-n4")
        n5 = os.path.join(basedir, command + "-n5")
        argv = ["--quiet", command, "--multiple", n4, n5]
        rc, out, err = self.run_tahoe(argv)
        self.failUnlessEqual(err, "")
        self.failUnlessEqual(out, "")
        self.failUnlessEqual(rc, 0)
        self.failUnless(os.path.exists(n4))
        self.failUnless(os.path.exists(os.path.join(n4, tac)))
        self.failUnless(os.path.exists(n5))
        self.failUnless(os.path.exists(os.path.join(n5, tac)))

        # make sure it rejects too many arguments without --multiple
        argv = [command, "basedir", "extraarg"]
        self.failUnlessRaises(usage.UsageError,
                              runner.runner, argv,
                              run_by_human=False)

        # when creating a non-client, there is no default for the basedir
        if not is_client:
            argv = [command]
            self.failUnlessRaises(usage.UsageError,
                                  runner.runner, argv,
                                  run_by_human=False)


    def test_node(self):
        self.do_create("node")

    def test_client(self):
        # create-client should behave like create-node --no-storage.
        self.do_create("client")

    def test_introducer(self):
        self.do_create("introducer")

    def test_key_generator(self):
        self.do_create("key-generator")

    def test_stats_gatherer(self):
        self.do_create("stats-gatherer")

    def test_subcommands(self):
        # no arguments should trigger a command listing, via UsageError
        self.failUnlessRaises(usage.UsageError,
                              runner.runner,
                              [],
                              run_by_human=False)


class RunNode(common_util.SignalMixin, unittest.TestCase, pollmixin.PollMixin,
              SkipMixin):
    # exercise "tahoe start", for both introducer, client node, and
    # key-generator, by spawning "tahoe start" as a subprocess. This doesn't
    # get us figleaf-based line-level coverage, but it does a better job of
    # confirming that the user can actually run "./bin/tahoe start" and
    # expect it to work. This verifies that bin/tahoe sets up PYTHONPATH and
    # the like correctly.

    # This doesn't work on cygwin (it hangs forever), so we skip this test
    # when we're on cygwin. It is likely that "tahoe start" itself doesn't
    # work on cygwin: twisted seems unable to provide a version of
    # spawnProcess which really works there.

    def workdir(self, name):
        basedir = os.path.join("test_runner", "RunNode", name)
        fileutil.make_dirs(basedir)
        return basedir

    def test_introducer(self):
        self.skip_if_cannot_daemonize()
        basedir = self.workdir("test_introducer")
        c1 = os.path.join(basedir, "c1")
        HOTLINE_FILE = os.path.join(c1, "suicide_prevention_hotline")
        TWISTD_PID_FILE = os.path.join(c1, "twistd.pid")
        INTRODUCER_FURL_FILE = os.path.join(c1, "introducer.furl")

        d = utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "create-introducer", "--basedir", c1], env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 0)
            # by writing this file, we get ten seconds before the node will
            # exit. This insures that even if the test fails (and the 'stop'
            # command doesn't work), the client should still terminate.
            open(HOTLINE_FILE, "w").write("")
            # now it's safe to start the node
        d.addCallback(_cb)

        def _then_start_the_node(res):
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "start", c1], env=os.environ)
        d.addCallback(_then_start_the_node)

        def _cb2(res):
            out, err, rc_or_sig = res

            open(HOTLINE_FILE, "w").write("")
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.

            # the parent (twistd) has exited. However, twistd writes the pid
            # from the child, not the parent, so we can't expect twistd.pid
            # to exist quite yet.

            # the node is running, but it might not have made it past the
            # first reactor turn yet, and if we kill it too early, it won't
            # remove the twistd.pid file. So wait until it does something
            # that we know it won't do until after the first turn.
        d.addCallback(_cb2)

        def _node_has_started():
            return os.path.exists(INTRODUCER_FURL_FILE)
        d.addCallback(lambda res: self.poll(_node_has_started))

        def _started(res):
            open(HOTLINE_FILE, "w").write("")
            self.failUnless(os.path.exists(TWISTD_PID_FILE))
            # rm this so we can detect when the second incarnation is ready
            os.unlink(INTRODUCER_FURL_FILE)
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "restart", c1], env=os.environ)
        d.addCallback(_started)

        def _then(res):
            out, err, rc_or_sig = res
            open(HOTLINE_FILE, "w").write("")
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.
        d.addCallback(_then)

        # again, the second incarnation of the node might not be ready yet,
        # so poll until it is
        d.addCallback(lambda res: self.poll(_node_has_started))

        # now we can kill it. TODO: On a slow machine, the node might kill
        # itself before we get a chance too, especially if spawning the
        # 'tahoe stop' command takes a while.
        def _stop(res):
            open(HOTLINE_FILE, "w").write("")
            self.failUnless(os.path.exists(TWISTD_PID_FILE))

            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "stop", c1], env=os.environ)
        d.addCallback(_stop)

        def _after_stopping(res):
            out, err, rc_or_sig = res
            open(HOTLINE_FILE, "w").write("")
            # the parent has exited by now
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.
            # the parent was supposed to poll and wait until it sees
            # twistd.pid go away before it exits, so twistd.pid should be
            # gone by now.
            self.failIf(os.path.exists(TWISTD_PID_FILE))
        d.addCallback(_after_stopping)

        def _remove_hotline(res):
            os.unlink(HOTLINE_FILE)
            return res
        d.addBoth(_remove_hotline)
        return d
    test_introducer.timeout = 480 # This hit the 120-second timeout on "François Lenny-armv5tel", then it hit a 240-second timeout on our feisty2.5 buildslave: http://allmydata.org/buildbot/builders/feisty2.5/builds/2381/steps/test/logs/test.log

    def test_client_no_noise(self):
        self.skip_if_cannot_daemonize()
        import pkg_resources
        try:
            pkg_resources.require("Twisted>=9.0.0")
        except pkg_resources.VersionConflict:
            raise unittest.SkipTest("We pass this test only with Twisted >= v9.0.0")
        basedir = self.workdir("test_client_no_noise")
        c1 = os.path.join(basedir, "c1")
        HOTLINE_FILE = os.path.join(c1, "suicide_prevention_hotline")
        TWISTD_PID_FILE = os.path.join(c1, "twistd.pid")
        PORTNUMFILE = os.path.join(c1, "client.port")

        d = utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "create-client", "--basedir", c1, "--webport", "0"], env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            errstr = "cc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            assert rc_or_sig == 0, errstr
            self.failUnlessEqual(rc_or_sig, 0)
            # By writing this file, we get forty seconds before the client will exit. This insures
            # that even if the 'stop' command doesn't work (and the test fails), the client should
            # still terminate.
            open(HOTLINE_FILE, "w").write("")
            open(os.path.join(c1, "introducer.furl"), "w").write("pb://xrndsskn2zuuian5ltnxrte7lnuqdrkz@127.0.0.1:55617/introducer\n")
            # now it's safe to start the node
        d.addCallback(_cb)

        def _start(res):
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "start", c1], env=os.environ)
        d.addCallback(_start)

        def _cb2(res):
            out, err, rc_or_sig = res
            errstr = "cc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            open(HOTLINE_FILE, "w").write("")
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr) # If you emit noise, you fail this test.
            self.failUnlessEqual(err, "", errstr)

            # the parent (twistd) has exited. However, twistd writes the pid
            # from the child, not the parent, so we can't expect twistd.pid
            # to exist quite yet.

            # the node is running, but it might not have made it past the
            # first reactor turn yet, and if we kill it too early, it won't
            # remove the twistd.pid file. So wait until it does something
            # that we know it won't do until after the first turn.
        d.addCallback(_cb2)

        def _node_has_started():
            return os.path.exists(PORTNUMFILE)
        d.addCallback(lambda res: self.poll(_node_has_started))

        # now we can kill it. TODO: On a slow machine, the node might kill
        # itself before we get a chance too, especially if spawning the
        # 'tahoe stop' command takes a while.
        def _stop(res):
            self.failUnless(os.path.exists(TWISTD_PID_FILE), (TWISTD_PID_FILE, os.listdir(os.path.dirname(TWISTD_PID_FILE))))
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "stop", c1], env=os.environ)
        d.addCallback(_stop)
        return d

    def test_client(self):
        self.skip_if_cannot_daemonize()
        basedir = self.workdir("test_client")
        c1 = os.path.join(basedir, "c1")
        HOTLINE_FILE = os.path.join(c1, "suicide_prevention_hotline")
        TWISTD_PID_FILE = os.path.join(c1, "twistd.pid")
        PORTNUMFILE = os.path.join(c1, "client.port")

        d = utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "create-node", "--basedir", c1, "--webport", "0"], env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 0)
            # By writing this file, we get sixty seconds before the client will exit. This insures
            # that even if the 'stop' command doesn't work (and the test fails), the client should
            # still terminate.
            open(HOTLINE_FILE, "w").write("")
            open(os.path.join(c1, "introducer.furl"), "w").write("pb://xrndsskn2zuuian5ltnxrte7lnuqdrkz@127.0.0.1:55617/introducer\n")
            # now it's safe to start the node
        d.addCallback(_cb)

        def _start(res):
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "start", c1], env=os.environ)
        d.addCallback(_start)

        def _cb2(res):
            out, err, rc_or_sig = res
            open(HOTLINE_FILE, "w").write("")
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.

            # the parent (twistd) has exited. However, twistd writes the pid
            # from the child, not the parent, so we can't expect twistd.pid
            # to exist quite yet.

            # the node is running, but it might not have made it past the
            # first reactor turn yet, and if we kill it too early, it won't
            # remove the twistd.pid file. So wait until it does something
            # that we know it won't do until after the first turn.
        d.addCallback(_cb2)

        def _node_has_started():
            return os.path.exists(PORTNUMFILE)
        d.addCallback(lambda res: self.poll(_node_has_started))

        def _started(res):
            open(HOTLINE_FILE, "w").write("")
            self.failUnless(os.path.exists(TWISTD_PID_FILE))
            # rm this so we can detect when the second incarnation is ready
            os.unlink(PORTNUMFILE)

            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "restart", c1], env=os.environ)
        d.addCallback(_started)

        def _cb3(res):
            out, err, rc_or_sig = res

            open(HOTLINE_FILE, "w").write("")
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.
        d.addCallback(_cb3)

        # again, the second incarnation of the node might not be ready yet,
        # so poll until it is
        d.addCallback(lambda res: self.poll(_node_has_started))

        # now we can kill it. TODO: On a slow machine, the node might kill
        # itself before we get a chance too, especially if spawning the
        # 'tahoe stop' command takes a while.
        def _stop(res):
            open(HOTLINE_FILE, "w").write("")
            self.failUnless(os.path.exists(TWISTD_PID_FILE), (TWISTD_PID_FILE, os.listdir(os.path.dirname(TWISTD_PID_FILE))))
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "stop", c1], env=os.environ)
        d.addCallback(_stop)

        def _cb4(res):
            out, err, rc_or_sig = res

            open(HOTLINE_FILE, "w").write("")
            # the parent has exited by now
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.
            # the parent was supposed to poll and wait until it sees
            # twistd.pid go away before it exits, so twistd.pid should be
            # gone by now.
            self.failIf(os.path.exists(TWISTD_PID_FILE))
        d.addCallback(_cb4)
        def _remove_hotline(res):
            os.unlink(HOTLINE_FILE)
            return res
        d.addBoth(_remove_hotline)
        return d

    def test_baddir(self):
        self.skip_if_cannot_daemonize()
        basedir = self.workdir("test_baddir")
        fileutil.make_dirs(basedir)

        d = utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "start", "--basedir", basedir], env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 1)
            self.failUnless("does not look like a node directory" in err, err)
        d.addCallback(_cb)

        def _then_stop_it(res):
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "stop", "--basedir", basedir], env=os.environ)
        d.addCallback(_then_stop_it)

        def _cb2(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 2)
            self.failUnless("does not look like a running node directory" in err)
        d.addCallback(_cb2)

        def _then_start_in_bogus_basedir(res):
            not_a_dir = os.path.join(basedir, "bogus")
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "start", "--basedir", not_a_dir], env=os.environ)
        d.addCallback(_then_start_in_bogus_basedir)

        def _cb3(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 1)
            self.failUnless("does not look like a directory at all" in err, err)
        d.addCallback(_cb3)
        return d

    def test_keygen(self):
        self.skip_if_cannot_daemonize()
        basedir = self.workdir("test_keygen")
        c1 = os.path.join(basedir, "c1")
        TWISTD_PID_FILE = os.path.join(c1, "twistd.pid")
        KEYGEN_FURL_FILE = os.path.join(c1, "key_generator.furl")

        d = utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "create-key-generator", "--basedir", c1], env=os.environ)
        def _cb(res):
            out, err, rc_or_sig = res
            self.failUnlessEqual(rc_or_sig, 0)
        d.addCallback(_cb)

        def _start(res):
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "start", c1], env=os.environ)
        d.addCallback(_start)

        def _cb2(res):
            out, err, rc_or_sig = res
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.

            # the parent (twistd) has exited. However, twistd writes the pid
            # from the child, not the parent, so we can't expect twistd.pid
            # to exist quite yet.

            # the node is running, but it might not have made it past the
            # first reactor turn yet, and if we kill it too early, it won't
            # remove the twistd.pid file. So wait until it does something
            # that we know it won't do until after the first turn.
        d.addCallback(_cb2)

        def _node_has_started():
            return os.path.exists(KEYGEN_FURL_FILE)
        d.addCallback(lambda res: self.poll(_node_has_started))

        def _started(res):
            self.failUnless(os.path.exists(TWISTD_PID_FILE))
            # rm this so we can detect when the second incarnation is ready
            os.unlink(KEYGEN_FURL_FILE)
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "restart", c1], env=os.environ)
        d.addCallback(_started)

        def _cb3(res):
            out, err, rc_or_sig = res
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.
        d.addCallback(_cb3)

        # again, the second incarnation of the node might not be ready yet,
        # so poll until it is
        d.addCallback(lambda res: self.poll(_node_has_started))

        # now we can kill it. TODO: On a slow machine, the node might kill
        # itself before we get a chance too, especially if spawning the
        # 'tahoe stop' command takes a while.
        def _stop(res):
            self.failUnless(os.path.exists(TWISTD_PID_FILE))
            return utils.getProcessOutputAndValue(bintahoe, args=["--quiet", "stop", c1], env=os.environ)
        d.addCallback(_stop)

        def _cb4(res):
            out, err, rc_or_sig = res
            # the parent has exited by now
            errstr = "rc=%d, OUT: '%s', ERR: '%s'" % (rc_or_sig, out, err)
            self.failUnlessEqual(rc_or_sig, 0, errstr)
            self.failUnlessEqual(out, "", errstr)
            # self.failUnlessEqual(err, "", errstr) # See test_client_no_noise -- for now we ignore noise.
            # the parent was supposed to poll and wait until it sees
            # twistd.pid go away before it exits, so twistd.pid should be
            # gone by now.
            self.failIf(os.path.exists(TWISTD_PID_FILE))
        d.addCallback(_cb4)
        return d
