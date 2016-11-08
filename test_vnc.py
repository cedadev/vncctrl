"""
Set environment variables according to pylons configuration.

Bootstraping the WPS configuration can be difficult as various environment
variables need to be set.  This module allows all configuration to be centralised
in pylons.config without extra wrapper scripts.
"""

# Standard library imports
import os, sys, commands, logging

# Third party imports
import vncctrl



def do():
    """
    Set VNC so that it connects to VNC server correctly.
    """
    # USER isn't set within mod_wsgi
    if 'USER' not in os.environ:
        os.environ['USER'] = "cwps"

    vnc_home = ".vncctrl"
    vncctrl.initDisplay(vncUserDir=vnc_home)

    print "\nVNC started. Environment variables set:"
    for var in ("DISPLAY", "XAUTHORITY"):
        print "   %s=%s" % (var, os.environ[var])

    print "\nNow testing connection:"
    for command in ("xhost", "xrandr --query"):
        print "\nrunning '%s'" % command
        os.system(command)

    print
do()
