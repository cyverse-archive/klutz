#!/usr/bin/env python

import os, sys
import os.path
import yaml
from subprocess import call

def exec_cmd(cmd, good_status=0):
    """Executes the 'cmd' list and returns the return value. Exits on a non-zero
    exit status. Yes, that's evil and will probably change."""
    print "-"*80
    printable_cmd = " ".join(cmd)
    print "Command: " + printable_cmd
    status = call(cmd, stdout=sys.__stdout__, stderr=sys.__stderr__)

    if status != good_status:
        sys.__stderr__.write(
            "ERROR: '%s' exited with a status of %i\n" % (printable_cmd, status)
        )
        sys.exit(status)
    else:
        return status

def symlink_key_file(keyfile="/vagrant/id_rsa"):
    """ Symlinks 'pubfile' (/vagrant/id_rsa by default) to ~/.ssh/. This
    allows git to run without requiring the user to enter a password.
    Well, potentially at least."""
    if not os.path.exists(keyfile):
        sys.__stderr__.write(
            "ERROR: %s does not exist." % keyfile
        )
        sys.exit(1)

    symlink_path = os.path.expanduser("~/.ssh/%s" % os.path.basename(keyfile))

    if not os.path.exists(symlink_path):
        os.symlink(pubfile, symlink_path)
    else:
        print symlink_path + " already exists, not symlinking."

class Git(object):
    """ Very basic wrapper class for git operations."""
    def __init__(self, refspec):
        self.refspec = refspec

    def clone(self, directory):
        """Clones the repository into 'directory'. If 'directory'
        already exists, then the clone operation is skipped. Returns the
        exit code of the clone command or 0 if the clone command is
        skipped."""
        if os.path.exists(directory):
            print directory + " already exists, skipping clone."
            return 0
        else:
            cmd = ["git", "clone", self.refspec, directory]
            return exec_cmd(cmd)

    def checkout(self, identifier):
        """Checks out the branch in the repository specificed by
        'identifier'. Returns the exit code of the 'git checkout'
        command."""
        return exec_cmd(["git", "checkout", identifier])

    def pull(self, pull_branch, repo="origin"):
        """Does a git pull of 'pull_branch' from 'repo', which is
        'origin' by default. Checks out 'pull_branch' first, so be
        careful with subsequent commands. Returns the exit code of the
        git pull command."""
        self.checkout(pull_branch)
        return exec_cmd(["git", "pull", repo, pull_branch])

    def merge(self, from_branch, to_branch, repo="origin"):
        """Does a git merge of from_branch into to_branch from repo.
        repo defaults to 'origin'. Checks out each branch first and
        pulls it, just to be sure. The repo will be on the to_branch
        after the operation is complete. Returns the exit code of the
        git-merge command."""
        self.checkout(from_branch)
        self.pull(from_branch, repo=repo)
        self.checkout(to_branch)
        self.pull(to_branch, repo=repo)
        return exec_cmd(["git", "merge", from_branch])

    def fetch(self):
        """Does a git fetch for the repo. Returns the exit code
        of the git fetch command."""
        return exec_cmd(["git", "fetch"])

    def push(self, push_branch, repo="origin"):
        """Does a git push of push_branch into repo. repo is "origin" by
        default. Checks out push_branch before pushing changes to it, so
        the repo will be on that branch after the command is done.
        Returns the exit code of the git push command."""
        self.checkout(push_branch)
        return exec_cmd(["git", "push", repo, push_branch])

if __name__ == "__main__":
    symlink_pub_file()
    g = Git("git@github.com:iPlantCollaborativeOpenSource/Donkey.git")
    g.clone("donkey")
    first_dir = os.getcwd()
    os.chdir("donkey")
    g.merge("dev", "donkzilla")
    g.push("donkzilla")
    os.chdir(first_dir)
