#!/usr/bin/env python

import os, sys
import os.path
import yaml
from subprocess import call

def exec_cmd(cmd, good_status=0):
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

def symlink_pub_file(pubfile="/vagrant/id_rsa"):
    if not os.path.exists(pubfile):
        sys.__stderr__.write(
            "ERROR: %s does not exist." % pubfile
        )
        sys.exit(1)

    symlink_path = os.path.expanduser("~/.ssh/%s" % os.path.basename(pubfile))
    print symlink_path

    if not os.path.exists(symlink_path):
        os.symlink(pubfile, symlink_path)
    else:
        print symlink_path + " already exists, not symlinking."

class Git(object):
    def __init__(self, refspec):
        self.refspec = refspec

    def clone(self, directory):
        if os.path.exists(directory):
            print directory + " already exists, skipping clone."
            return 0
        else:
            cmd = ["git", "clone", self.refspec, directory]
            return exec_cmd(cmd)

    def checkout(self, identifier):
        return exec_cmd(["git", "checkout", identifier])

    def pull(self, pull_branch, repo="origin"):
        self.checkout(pull_branch)
        return exec_cmd(["git", "pull", repo, pull_branch])

    def merge(self, from_branch, to_branch, repo="origin"):
        self.checkout(from_branch)
        self.pull(from_branch, repo=repo)
        self.checkout(to_branch)
        self.pull(to_branch, repo=repo)
        return exec_cmd(["git", "merge", from_branch])

    def fetch(self):
        return exec_cmd(["git", "fetch"])

    def push(self, push_branch, repo="origin"):
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
