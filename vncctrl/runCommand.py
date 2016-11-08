#!/usr/bin/python

"""
 this module provides runCommand.runCommand, which is similar to 
 command.getstatusoutput, except this one invokes the command without
 a shell, instead of using os.popen() which uses a shell

 For usage info, see doc string for runCommand()

"""
#
# Alan Iwi is to blame for this module
#

import os
import sys
import select
import signal


def runCommand(cmd,
               input="",
               waitChildren = True):
    """
    runCommand(cmd) -> status, output, error

    returns status, output of executing cmd directly without a shell.

    Inputs:

      cmd is a list/tuple containing command and arguments
      (or cmd can be a string, but in that case the command takes no arguments)

      input is a string

      waitChildren is a boolean.  If set True, then if the process terminates
        having forked child processes still accessing the same open I/O
        streams, then the function will keep going until the pipes are finally
        closed by the child processes.  But if False, then once the main
        process terminates the function will quickly return and just return the
        output so far.

    status is an integer
    output is a string
    
    """

    pread, cwrite = os.pipe()
    preaderr, cwriteerr = os.pipe()
    cread, pwrite = os.pipe()
    
    pid = os.fork()
    if (pid == 0):
        # child
        os.close(pread)
        os.close(preaderr)
        os.close(pwrite)
        os.dup2(cread, 0)
        os.dup2(cwrite, 1)  #stdout
        os.dup2(cwriteerr, 2)  #stderr

        if type(cmd) == str:
            command, args = cmd, (cmd,)
        else:
            command, args = cmd[0], cmd

        try:
            os.execvp(command, args)
        except os.error, (errno, message):
            os.write(2, "exec: %s: %s\n" % (command, message))
            os.close(1)
            os.close(2)
            os._exit(1)

    # parent
    os.close(cwrite)
    os.close(cwriteerr)
    os.close(cread)

    setNonBlocking(pwrite)

    output = ""
    error = ""

    rlist = [pread, preaderr]
    wlist = [pwrite]

    chunksize = 2048

    #  main loop: keep reading and/or writing data until one of two things
    #  happen:
    #
    #    a) all the original pipes have been closed by the child process 
    #        and its children if any
    #
    #    b) we test and find out that the main child process has exited,
    #        having been requested not to wait for its children; in this case
    #        there may still be processes that have open filehandles on the
    #        pipes, but we ignore them

    if waitChildren:
        selectTimeout = None  # select.select() will block until there is data
                              # (or one of the pipes gets closed)
    else:
        selectTimeout = 0.1  # force a timeout (value in seconds), so 
                             # that we can also periodically get back to
                             # testing whether the child exited

    status = None  # output status - will write an integer 
                   # once the process terminates

    while (status == None) and (wlist or rlist):

        if not waitChildren:
            # try to see whether the child process has exited
            pidData = os.waitpid(pid, os.WNOHANG)
            if pidData[0] == pid:
                # child process has exited, but may have left file descriptors
                # open if it has forked; do one last non-blocking check for
                # read data, and then do not wait for the grandchildren
                status = pidData[1]
                wlist = []  # don't care about writing any more
                selectTimeout = 0  # select.select() will not wait

        # test for either data ready to read, or space to write
        rReady, wReady, xReady = select.select(rlist, wlist, [],
                                               selectTimeout)

        # read from child - could be from stdout or stderr
        if rReady:
            for fd in rReady:
                dataread = os.read(fd, chunksize)
                if len(dataread) == 0:
                    os.close(fd)
                    rlist.remove(fd)
                else:
                    if fd == pread:
                        output += dataread
                    elif fd == preaderr:
                        error += dataread

        # write to child
        if wReady:
            if len(input) != 0:
                charswritten = os.write(pwrite, input)
                input = input[charswritten : ]
            else:
                os.close(pwrite)
                wlist = []


    # call waitpid unless a previous call already got the exit status
    if status == None:
        pid, status = os.waitpid(pid, 0)

    return status / 256, output, error


def setNonBlocking(fd):
    import fcntl, os
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK | flags)


#-------------------------------------------------------------
# Test cases follow.

if __name__ == "__main__":

    def show(string, max=2000):
        length = len(string)
        if length > max:
            return "(%d bytes)" % length
        else:
            return string

    def runCommand_wrap(cmd, input="", **kwargs):
        print 'Command: ', cmd

        print 'STDIN: '
        print show(input)
        (status, output, error) = runCommand(cmd, input, **kwargs)
        print 'Status: ', status

        print 'STDOUT: '
        print show(output)
        print 'STDERR: '
        print show(error)
        print "=========="
        return status, output, error
    

    # this command should succeed
    runCommand_wrap(('rev'), '20\n14\n123')

    # this command should also succeed, and has a command-line option
    runCommand_wrap(('sort', '-n'), '20\n14\n123')

    # this command should succeed with no output
    runCommand_wrap(('true'))

    # this command should succeed, and has no input
    runCommand_wrap(('head', '/etc/passwd'))

    # this command should exec but then return an error
    runCommand_wrap(('cat', '/etc/asdfasdfasdfasdf'))

    # this command should fail to exec
    runCommand_wrap(('asdjklasdfjklasdf'))

    s=''
    for i in range(0, 100000):
        s += 'a'
    # this command will read/write a lot of data - need to do so in alternating
    # chunks.
    (status, output, error) = runCommand_wrap('cat', s)

    # this will keep going till we kill Xvnc itself
    runCommand_wrap('vncserver')
    
    # this will return once vncserver script exits
    runCommand_wrap('vncserver',
                     waitChildren = False)
