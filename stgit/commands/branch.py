"""Branch command
"""

__copyright__ = """
Copyright (C) 2005, Chuck Lever <cel@netapp.com>

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

import sys, os, time, re
from optparse import OptionParser, make_option

from stgit.commands.common import *
from stgit.utils import *
from stgit.out import *
from stgit import stack, git, basedir


help = 'manage patch stacks'
usage = """%prog [options] branch-name [commit-id]

Create, clone, switch between, rename, or delete development branches
within a git repository.  By default, a single branch called 'master'
is always created in a new repository.  This subcommand allows you to
manage several patch series in the same repository via GIT branches.

When displaying the branches, the names can be prefixed with
's' (StGIT managed) or 'p' (protected).

If not given any options, switch to the named branch."""

directory = DirectoryGotoToplevel()
options = [make_option('-c', '--create',
                       help = 'create a new development branch',
                       action = 'store_true'),
           make_option('--clone',
                       help = 'clone the contents of the current branch',
                       action = 'store_true'),
           make_option('--delete',
                       help = 'delete an existing development branch',
                       action = 'store_true'),
           make_option('-d', '--description',
                       help = 'set the branch description'),
           make_option('--force',
                       help = 'force a delete when the series is not empty',
                       action = 'store_true'),
           make_option('-l', '--list',
                       help = 'list branches contained in this repository',
                       action = 'store_true'),
           make_option('-p', '--protect',
                       help = 'prevent StGIT from modifying this branch',
                       action = 'store_true'),
           make_option('-r', '--rename',
                       help = 'rename an existing development branch',
                       action = 'store_true'),
           make_option('-u', '--unprotect',
                       help = 'allow StGIT to modify this branch',
                       action = 'store_true')]


def __is_current_branch(branch_name):
    return crt_series.get_name() == branch_name

def __print_branch(branch_name, length):
    initialized = ' '
    current = ' '
    protected = ' '

    branch = stack.Series(branch_name)

    if branch.is_initialised():
        initialized = 's'
    if __is_current_branch(branch_name):
        current = '>'
    if branch.get_protected():
        protected = 'p'
    out.stdout(current + ' ' + initialized + protected + '\t'
               + branch_name.ljust(length) + '  | ' + branch.get_description())

def __delete_branch(doomed_name, force = False):
    doomed = stack.Series(doomed_name)

    if doomed.get_protected():
        raise CmdException, 'This branch is protected. Delete is not permitted'

    out.start('Deleting branch "%s"' % doomed_name)

    if __is_current_branch(doomed_name):
        raise CmdException('Cannot delete the current branch')

    doomed.delete(force)

    out.done()

def func(parser, options, args):

    if options.create:

        if len(args) == 0 or len(args) > 2:
            parser.error('incorrect number of arguments')

        check_local_changes()
        check_conflicts()
        check_head_top_equal(crt_series)

        tree_id = None
        if len(args) >= 2:
            parentbranch = None
            try:
                branchpoint = git.rev_parse(args[1])

                # parent branch?
                head_re = re.compile('refs/(heads|remotes)/')
                ref_re = re.compile(args[1] + '$')
                for ref in git.all_refs():
                    if head_re.match(ref) and ref_re.search(ref):
                        # args[1] is a valid ref from the branchpoint
                        # setting above
                        parentbranch = args[1]
                        break;
            except git.GitException:
                # should use a more specific exception to catch only
                # non-git refs ?
                out.info('Don\'t know how to determine parent branch'
                         ' from "%s"' % args[1])
                # exception in branch = rev_parse() leaves branchpoint unbound
                branchpoint = None

            tree_id = git_id(crt_series, branchpoint or args[1])

            if parentbranch:
                out.info('Recording "%s" as parent branch' % parentbranch)
            else:
                out.info('Don\'t know how to determine parent branch'
                         ' from "%s"' % args[1])                
        else:
            # branch stack off current branch
            parentbranch = git.get_head_file()

        if parentbranch:
            parentremote = git.identify_remote(parentbranch)
            if parentremote:
                out.info('Using remote "%s" to pull parent from'
                         % parentremote)
            else:
                out.info('Recording as a local branch')
        else:
            # no known parent branch, can't guess the remote
            parentremote = None

        stack.Series(args[0]).init(create_at = tree_id,
                                   parent_remote = parentremote,
                                   parent_branch = parentbranch)

        out.info('Branch "%s" created' % args[0])
        return

    elif options.clone:

        if len(args) == 0:
            clone = crt_series.get_name() + \
                    time.strftime('-%C%y%m%d-%H%M%S')
        elif len(args) == 1:
            clone = args[0]
        else:
            parser.error('incorrect number of arguments')

        check_local_changes()
        check_conflicts()
        check_head_top_equal(crt_series)

        out.start('Cloning current branch to "%s"' % clone)
        crt_series.clone(clone)
        out.done()

        return

    elif options.delete:

        if len(args) != 1:
            parser.error('incorrect number of arguments')
        __delete_branch(args[0], options.force)
        return

    elif options.list:

        if len(args) != 0:
            parser.error('incorrect number of arguments')

        branches = git.get_heads()
        branches.sort()

        if branches:
            out.info('Available branches:')
            max_len = max([len(i) for i in branches])
            for i in branches:
                __print_branch(i, max_len)
        else:
            out.info('No branches')
        return

    elif options.protect:

        if len(args) == 0:
            branch_name = crt_series.get_name()
        elif len(args) == 1:
            branch_name = args[0]
        else:
            parser.error('incorrect number of arguments')
        branch = stack.Series(branch_name)

        if not branch.is_initialised():
            raise CmdException, 'Branch "%s" is not controlled by StGIT' \
                  % branch_name

        out.start('Protecting branch "%s"' % branch_name)
        branch.protect()
        out.done()

        return

    elif options.rename:

        if len(args) != 2:
            parser.error('incorrect number of arguments')

        if __is_current_branch(args[0]):
            raise CmdException, 'Renaming the current branch is not supported'

        stack.Series(args[0]).rename(args[1])

        out.info('Renamed branch "%s" to "%s"' % (args[0], args[1]))

        return

    elif options.unprotect:

        if len(args) == 0:
            branch_name = crt_series.get_name()
        elif len(args) == 1:
            branch_name = args[0]
        else:
            parser.error('incorrect number of arguments')
        branch = stack.Series(branch_name)

        if not branch.is_initialised():
            raise CmdException, 'Branch "%s" is not controlled by StGIT' \
                  % branch_name

        out.info('Unprotecting branch "%s"' % branch_name)
        branch.unprotect()
        out.done()

        return

    elif options.description is not None:

        if len(args) == 0:
            branch_name = crt_series.get_name()
        elif len(args) == 1:
            branch_name = args[0]
        else:
            parser.error('incorrect number of arguments')
        branch = stack.Series(branch_name)

        if not branch.is_initialised():
            raise CmdException, 'Branch "%s" is not controlled by StGIT' \
                  % branch_name

        branch.set_description(options.description)

        return

    elif len(args) == 1:

        if __is_current_branch(args[0]):
            raise CmdException, 'Branch "%s" is already the current branch' \
                  % args[0]

        check_local_changes()
        check_conflicts()
        check_head_top_equal(crt_series)

        out.start('Switching to branch "%s"' % args[0])
        git.switch_branch(args[0])
        out.done()
        return

    # default action: print the current branch
    if len(args) != 0:
        parser.error('incorrect number of arguments')

    print crt_series.get_name()
