# -*- coding: utf-8 -*-

__copyright__ = """
Copyright (C) 2007, Karl Hasselström <kha@treskal.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""

import datetime, os, subprocess

from  stgit.out import *

class RunException(Exception):
    """Thrown when something bad happened when we tried to run the
    subprocess."""
    pass

_all_log_modes = ['debug', 'profile']
_log_mode = os.environ.get('STGIT_SUBPROCESS_LOG', '')
if _log_mode and not _log_mode in _all_log_modes:
    out.warn(('Unknown log mode "%s" specified in $STGIT_SUBPROCESS_LOG.'
              % _log_mode),
             'Valid values are: %s' % ', '.join(_all_log_modes))

class Run:
    exc = RunException
    def __init__(self, *cmd):
        self.__cmd = list(cmd)
        for c in cmd:
            if type(c) != str:
                raise Exception, 'Bad command: %r' % cmd
        self.__good_retvals = [0]
        self.__env = None
        self.__indata = None
        self.__discard_stderr = False
    def __log_start(self):
        if _log_mode == 'debug':
            out.start('Running subprocess %s' % self.__cmd)
        elif _log_mode == 'profile':
            out.start('Running subprocess %s' % self.__cmd[0])
            self.__starttime = datetime.datetime.now()
    def __log_end(self, retcode):
        if _log_mode == 'debug':
            out.done('return code: %d' % retcode)
        elif _log_mode == 'profile':
            duration = datetime.datetime.now() - self.__starttime
            out.done('%1.3f s' % (duration.microseconds/1e6 + duration.seconds))
    def __check_exitcode(self):
        if self.exitcode not in self.__good_retvals:
            raise self.exc('%s failed with code %d'
                           % (self.__cmd[0], self.exitcode))
    def __run_io(self):
        """Run with captured IO."""
        self.__log_start()
        try:
            p = subprocess.Popen(self.__cmd, env = self.__env,
                                 stdin = subprocess.PIPE,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE)
            outdata, errdata = p.communicate(self.__indata)
            self.exitcode = p.returncode
        except OSError, e:
            raise self.exc('%s failed: %s' % (self.__cmd[0], e))
        if errdata and not self.__discard_stderr:
            out.err_raw(errdata)
        self.__log_end(self.exitcode)
        self.__check_exitcode()
        return outdata
    def __run_noio(self):
        """Run without captured IO."""
        assert self.__indata == None
        self.__log_start()
        try:
            p = subprocess.Popen(self.__cmd, env = self.__env)
            self.exitcode = p.wait()
        except OSError, e:
            raise self.exc('%s failed: %s' % (self.__cmd[0], e))
        self.__log_end(self.exitcode)
        self.__check_exitcode()
    def returns(self, retvals):
        self.__good_retvals = retvals
        return self
    def discard_stderr(self, discard = True):
        self.__discard_stderr = discard
        return self
    def env(self, env):
        self.__env = dict(os.environ)
        self.__env.update(env)
        return self
    def raw_input(self, indata):
        self.__indata = indata
        return self
    def input_lines(self, lines):
        self.__indata = ''.join(['%s\n' % line for line in lines])
        return self
    def no_output(self):
        outdata = self.__run_io()
        if outdata:
            raise self.exc, '%s produced output' % self.__cmd[0]
    def discard_output(self):
        self.__run_io()
    def raw_output(self):
        return self.__run_io()
    def output_lines(self):
        outdata = self.__run_io()
        if outdata.endswith('\n'):
            outdata = outdata[:-1]
        if outdata:
            return outdata.split('\n')
        else:
            return []
    def output_one_line(self):
        outlines = self.output_lines()
        if len(outlines) == 1:
            return outlines[0]
        else:
            raise self.exc('%s produced %d lines, expected 1'
                           % (self.__cmd[0], len(outlines)))
    def run(self):
        """Just run, with no IO redirection."""
        self.__run_noio()
    def xargs(self, xargs):
        """Just run, with no IO redirection. The extra arguments are
        appended to the command line a few at a time; the command is
        run as many times as needed to consume them all."""
        step = 100
        basecmd = self.__cmd
        for i in xrange(0, len(xargs), step):
            self.__cmd = basecmd + xargs[i:i+step]
            self.__run_noio()
        self.__cmd = basecmd