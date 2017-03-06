import os
import re
import string
import glob
import time
import signal
import random

from runCommand import runCommand

"""
A module to get a VNC session

The main usage is:

   import vncctrl
   vncctrl.initdisplay()

This will ensure that a VNC session is started if not already, and set the
necessary environment variables so that X clients will use it.

But if the calling code instantiates class VncCtrl in this module, a number of
other methods are available.
"""


class _Regexps:
    #pidFile = re.compile(r'(:[0-9]+)\.pid')
    pidFile = re.compile(r'(.*)\.pid')
    desktop = re.compile(r'desktop is ([^\s]+)')

class _Paths:
    xvnc = '/usr/bin/Xvnc'
    xhost = '/usr/bin/xhost'
    null = '/dev/null'
    vncpasswd = '/usr/bin/vncpasswd'
    perl = '/usr/bin/perl'
    
    # vncserver path is relative to this python script
    vncserver = os.path.join(os.path.dirname(__file__), 'vncserver/vncserver')


class VncCtrl:

    """
    a class for controlling VNC server

    v = VncCtrl()

    optional args include:

        vncUserDir (string) 
             Directory for VNC-related files, defaults to $HOME/.vncctrl

        verbose (boolean)
             Whether to print additional info, default False

        promptPassword (boolean)
             Whether to prompt for a password if the VNC passwd file doesn't
             exist.  If not set, and it doesn't exist, a passwd file with a
             random password will be used, which will preclude connecting a
             viewer to the display.

        extraArgs (list)
             Args to pass through to the vncserver script when starting a
             server.  NB does not prevent getDisplay() from returning a
             display that was previously opened using different args.
    """

    def __init__(self,
                 vncUserDir = None,
                 verbose = False,
                 promptPassword = False,
                 extraArgs = []):

        if vncUserDir:
            self.vncUserDir = vncUserDir
        else:
            self.vncUserDir = self._defaultVncUserDir()

        self.xauthFile = os.path.join(self.vncUserDir,
                                      "Xauthority")

        self.promptPassword = promptPassword
        self.verbose = verbose
        self.extraArgs = extraArgs

    def _defaultVncUserDir(self):
        # default VNC user dir; note this deliberately differs from 
        # the default used by vncserver script
        return os.path.join(os.environ["HOME"], ".vncctrl")


    def startServer(self):
        """
        Start an instance (unconditionally)
        returns display
        """
        self._ensurePasswordFile()
        
        args = ['-localhost',
                '-userdir', self.vncUserDir,
                '-xauthority', self.xauthFile,
                '-socat']

        #Note: perl is needed because when executing within an egg
        #      vncserver will not be marked executable.
        command = [_Paths.perl, _Paths.vncserver] + args + self.extraArgs
        status, output, error = runCommand(command,
                                           waitChildren=False)

        # Check correct status returned
        if status != 0:
            raise RuntimeError('Launching vncserver failed.\nStatus %d\nstdout: %s\nstderr: %s' %
                               (status, output, error))

        # parse message on stderr
        m = _Regexps.desktop.search(error)
        if m:
            display = m.group(1)
            if self.verbose:
                print "started server on %s" % display
            if self.testDisplay(display):
                return display
            raise RuntimeError("display just started on %s is not responding"
                               % display)

        else:
            raise RuntimeError("apparently launched vncserver " + 
                               "but could not determine display name")

    def killServer(self, display):
        """
        Kills server running on specified display
        """
        raise NotImplementedError
        
    def initDisplay(self):
        """
        get a working display (whether existing or newly created), 
        and set the environment variables so the calling process can use it
        """
        display = self.getDisplay()

        os.environ["DISPLAY"] = display
        os.environ["XAUTHORITY"] = self.xauthFile

        if self.verbose:
            for var in ['DISPLAY', 'XAUTHORITY']:
                print "%s=%s" % (var, os.environ[var])

        return display

    def getDisplay(self):
        """
        get a working display - either an existing one or a new one
        """
        for display in self.listDisplays():
            if self.testDisplay(display):
                if self.verbose:
                    print "Got an existing working display on %s" % display
                return display
        if self.verbose:
            print "Not found any existing working display"

        return self.startServer()

    def listDisplays(self):
        """
        Get list of display numbers on which there *may* be a Xvnc instance
        running.  This routine does elementary checking that the processes
        listed in the pid files still exist (and removes any that don't),
        but does not attempt to connect to them
        """
        pidFiles = self._listPidFiles()
        displays = []
        for pidFile in pidFiles:
            pid = pidFile.getPid()
            if self._pidIsMyXvnc(pid):
                displays.append(pidFile.getDisplay())
            else:
                # tidy up
                pidFile.remove()
        if self.verbose:
            print "Existing displays: %s" % displays
        return displays

    def testDisplay(self, display):
        """
        Test the server running on specified display

        Returns:  True -- it works
                  False -- it doesn't


        """

        # Some tedious low-level code in this routine, but the basic idea 
        # is that we try to run an 'xhost' command (without any arguments)
        # just as a way to see if we can connect.  This is done in a child
        # process; the parent waits for a bit for it to finish, and tests
        # the return code, or after about a second it gives up waiting and
        # assumes that it's not going to work.

        if self.verbose:
            print "Testing display %s" % display
        
        # On many servers the display name will exclude the localhost so remove 
        # hostname for this test
        display = ":" + display.split(":")[1]

        pid = os.fork()
        if not pid:
            # ---child---

            # discard output
            fhNull = os.open(_Paths.null, os.O_RDWR)
            os.dup2(fhNull, 1)  # stdout
            os.dup2(fhNull, 2)  # stderr

            # and run xhost
            os.putenv("DISPLAY", display)
            os.putenv("XAUTHORITY", self.xauthFile)
            os.execv(_Paths.xhost, ["xhost"])

            # exec failed
            os._exit(1)

        # --- parent ---
        for sleepTime in [0.01, 0.05, 0.1, 0.9]:
            time.sleep(sleepTime)
            pidW, status = os.waitpid(pid, os.WNOHANG)
            if pidW == pid:
                ifSuccess = (status == 0)
                if self.verbose:
                    if ifSuccess:
                        print "Display %s allowed connection" % display
                    else:
                        print "Display %s refused connection" % display

                return ifSuccess

        # at this point we give up waiting and kill the child proces
        os.kill(pid, signal.SIGKILL)

        # wait for it, to avoid zombies
        os.waitpid(pid, 0)

        if self.verbose:
            print "No response from display %s" % display

        return False
       
    def _ensurePasswordFile(self):
        """
        Ensure there is a password file in the userdir

        The vncserver wrapper is going to prompt for it if it's not there,
        and that's a bad place to prompt as we will be capturing the output
        """
        passwdFile = os.path.join(self.vncUserDir, "passwd")
        if not os.path.exists(passwdFile):
            if not os.path.exists(self.vncUserDir):
                os.mkdir(self.vncUserDir, 0700)
            if self.promptPassword:
                gotone = False
                while not gotone:
                    if os.system("%s %s" % (_Paths.vncpasswd, passwdFile)) == 0:
                        gotone = True
            else:
                self._makeRandomPasswordFile(passwdFile)


    def _makeRandomPasswordFile(self, filename):
        password = ""
        for i in range(8):
            password += "%c" % random.randrange(32, 128)
        status, output, error = runCommand([_Paths.vncpasswd, '-f'],
                                           input="%s\n" % password)
        fh = open(filename, "w")
        fh.write(output)
        fh.close()
        os.chmod(filename, 0600)

    def _pidIsMyXvnc(self, pid):
        """
        Test if PID corresponds to an Xvnc process owned by invoking user
        """
        dirName = "/proc/%d" % pid
        try:
            if not os.path.exists(dirName):
                return False
            if os.stat(dirName).st_uid != os.getuid():
                return False
            if os.readlink("%s/exe" % dirName) != _Paths.xvnc:
                return False
            return True
        except OSError:
            return False
    
    def _listPidFiles(self):
        filenames = glob.glob("%s/%s:*.pid" %
                                  (self.vncUserDir, self._getHostName()))
        return map(_PidFile, filenames)            

    def _getHostName(self):
        status, output, error = runCommand("/bin/hostname")
        return output.replace("\n", "")

        
class _PidFile:

    def __init__(self, filename):
        self.filename = filename

    def getPid(self):
        """
        Parse contents to get PID
        """
        try:
            fh = open(self.filename)
        except OSError:
            return None
        line = fh.readline()
        try:
            return string.atoi(line)  # trailing newline doesn't matter
        except ValueError:
            return None
        
    def getDisplay(self):
        """
        Parse filename to get display
        """
        m = _Regexps.pidFile.match(os.path.basename(self.filename))
        if m:
            return m.group(1)
        else:
            return None

    def remove(self):
        os.remove(self.filename)


def initDisplay(*args, **kwargs):
    """
    get a working VNC display (whether existing or newly created), 
    and set the environment variables so the calling process can use it

    For optional arguments, see docstring of the VncCtrl class in this
    module.
    """
    v = VncCtrl(*args, **kwargs)
    v.initDisplay()


def main():
    initDisplay(verbose = True,
                vncUserDir = '/tmp/myvnc',
                extraArgs = ['-geometry', '800x800'],
                promptPassword = False)
    print "Display is %s" % os.environ["DISPLAY"]
#    os.system("xrandr --query")

if __name__ == '__main__':
    main()
