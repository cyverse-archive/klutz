#!/usr/bin/env python

import os, sys
import os.path
import argparse
import yaml
from subprocess import call
import project_data as pd
from multiprocessing import Process

import pprint

JAVA_HOME = '/usr/lib/jvm/java-6-openjdk-amd64/'

class DependencyMismatchException(Exception):
    """Thrown when the version number in a dependency doesn't match the version
    number in the corresponding repository."""
    pass

def exec_cmd(cmd, good_status=0, stdout=sys.__stdout__, stderr=sys.__stderr__):
    """Executes the 'cmd' list and returns the return value. Exits on a
    non-zero exit status. Yes, that's evil and will probably change."""
    print >> stdout, "-"*80
    printable_cmd = " ".join(cmd)
    print >> stdout, "Command: " + printable_cmd
    status = call(cmd, stdout=stdout, stderr=stderr)

    if status != good_status:
        raise IOError(
            "'%s' exited with a status of %i" % (printable_cmd, status)
        )
    else:
        return status

def symlink_key_file(keyfile="/vagrant/id_rsa"):
    """ Symlinks 'pubfile' (/vagrant/id_rsa by default) to ~/.ssh/. This
    allows git to run without requiring the user to enter a password.
    Well, potentially at least."""
    print "Attempting to symlink", keyfile
    if not os.path.exists(keyfile):
        raise IOError("%s does not exist." % keyfile)

    symlink_path = os.path.expanduser("~/.ssh/%s" % os.path.basename(keyfile))

    if not os.access(os.path.dirname(symlink_path), os.W_OK):
        raise IOError(os.path.dirname(symlink_path) + " is not writeable.")

    if not os.path.exists(symlink_path):
        os.symlink(keyfile, symlink_path)
    else:
        print symlink_path + " already exists, not symlinking."

def parse_yaml(yaml_path="/vagrant/repos.yaml"):
    full_path = os.path.abspath(yaml_path)

    if not os.path.exists(full_path):
        raise IOError(full_path + " does not exist.")

    if not os.access(full_path, os.R_OK):
        raise IOError(full_path + " is not readable.")

    return yaml.load(open(full_path, 'r'))

def parse_command_line():
    p = argparse.ArgumentParser(description="Creates code drops.")
    p.add_argument(
        '-c', '--config', default="/vagrant/repos.yaml",
        help="Path to the configuration file."
    )
    p.add_argument(
        '-k', '--keyfile', default="/vagrant/id_rsa",
        help="Path to private key file for git."
    )
    p.add_argument(
        '--merge', dest='merge', action='store_true',
        help="Turns on merging."
    )
    p.add_argument(
        '--no-merge', dest='merge', action='store_false',
        help="Turns off merging."
    )
    p.add_argument(
        '--push', dest='push', action='store_true',
        help="Turns on pushing."
    )
    p.add_argument(
        '--no-push', dest='push', action='store_false',
        help="Turns off pushing after tagging and merging."
    )
    p.add_argument(
        '--tag', help="What to tag the repos with."
    )
    p.add_argument(
        '--build', dest='build', action='store_true',
        help="Turns on building."
    )
    p.add_argument(
        '--no-build', dest='build', action='store_false',
        help="Turns off building."
    )
    p.set_defaults(push=True, merge=True, build=True)
    return p.parse_args()

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

    def tag(self, tag_branch, tag):
        """Does a git tag of tag_branch with tag. Checks out tag_branch.
        Returns the exit code of the tag command."""
        self.checkout(tag_branch)
        return exec_cmd(["git", "tag", "-a", tag, "-m", tag])

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

def merge_and_tag(options, cfg):
    """Performs all merging and tagging operations. 'options' is the
    object returned by parse_command_line() and 'cfg' should be the
    object returned after parsing the yaml config file."""
    for proj in cfg['projects']:
        print "="*80
        proj_name = proj['name']
        proj_ref = proj['refspec']

        g = Git(proj_ref)
        g.clone(proj_name)
        first_dir = os.getcwd()
        os.chdir(proj_name)

        if proj.has_key('merge') and options.merge:
            merge_from = proj['merge']['from']
            merge_to = proj['merge']['to']
            g.merge(merge_from, merge_to)

        if options.tag and options.merge and proj.has_key('merge'):
            g.tag(proj['merge']['to'], options.tag)

        if options.push:
            g.push(merge_to)

        os.chdir(first_dir)

def info_for(proj):
    """Obtains the details for a project."""
    proj_name = proj['name']

    first_dir = os.getcwd()
    os.chdir(proj_name)

    validate_version = proj['validate_version']
    build = proj['build']
    if os.path.exists('project.clj'):
        proj_info = pd.LeinProjectData('project.clj', validate_version, build)
    elif os.path.exists('pom.xml'):
        proj_info = pd.MvnProjectData('pom.xml', validate_version, build)
    else:
        proj_info = pd.ProjectData(proj_name, proj_name, '', [],
                                   validate_version, build)

    os.chdir(first_dir)

    return proj_info

def build_proj_name_dictionary(proj_info):
    """Builds a dictionary that maps group IDs and artifact IDs to project
    names."""
    return {
        (value.group_id,value.artifact_id):key
        for key, value in proj_info.iteritems()
    }

def validate_dependency_versions(proj_info, proj_names):
    """Verifies that the versions for all project dependencies that correspond
    to repositories being built match the version numbers in the repositories."""
    for proj in proj_info.values():
        for dep in proj.dependencies:
            k = (dep.group_id, dep.artifact_id)
            if k in proj_names:
                dep_proj = proj_info[proj_names[k]]
                if dep_proj.validate_version and dep.version != dep_proj.version:
                    raise DependencyMismatchException(
                        '{}/{}: {}/{} {} requested but {} provided'.format(
                            proj.group_id, proj.artifact_id, dep.group_id,
                            dep.artifact_id, dep.version, dep_proj.version
                        )
                    )

def deps_satisfied(info, proj_names, build_set):
    """Determines if the dependencies have been satisfied for a project."""
    remaining_deps = [
        dep for dep in info.dependencies
        if (dep.group_id,dep.artifact_id) in proj_names
        and not proj_names[(dep.group_id,dep.artifact_id)] in build_set
    ]
    return len(remaining_deps) == 0

def generate_build_list(proj_info, proj_names):
    """Generates the list that determines the build order for all of the
    projects."""
    selected_projects = set()
    build_list = []
    while len(selected_projects) < len(proj_info):
        build_group = [
            name for name, info in proj_info.iteritems()
            if not name in selected_projects
            and deps_satisfied(info, proj_names, selected_projects)
        ]
        for project in build_group:
            selected_projects.add(project)
        build_list.append(build_group)
    return build_list

def build_project(proj_name, proj):
    """Builds a project."""
    outfile = '{}.out'.format(proj_name)
    errfile = '{}.err'.format(proj_name)

    with open(outfile, 'w') as out, open(errfile, 'w') as err:
        first_dir = os.getcwd()
        os.chdir(proj_name)


        for cmd in proj.build:
            exec_cmd(cmd, stdout=out, stderr=err)

        os.chdir(first_dir)

def start_build(proj_name, proj):
    """Starts a project build in a subprocess."""
    print '='*80
    print 'building {}...'.format(proj_name)
    proc = Process(target = build_project, args=(proj_name, proj))
    proc.start()
    return proc

def build_projects_in_group(proj_info, build_group):
    """Builds all of the projects in a group of projects. It must be possible
    to build all of the projects in the group simultaneously."""
    build_recs = [
        (proj_name, start_build(proj_name, proj_info[proj_name]))
        for proj_name in build_group
    ]
    for proj_name, proc in build_recs:
        proc.join()
    build_failed = False
    for proj_name, proc in build_recs:
        if proc.exitcode != 0:
            print >> sys.stderr, '** Unable to build {}'.format(proj_name)
            build_failed = True
    if build_failed:
        msg = '** Some builds failed. Please review the output files.'
        print >> sys.stderr, msg
        sys.exit(1)

def build(cfg):
    """Builds all of the repositories in the list of repositories. 'cfg'
    is the object returned after parsing the yaml config file."""
    proj_info = {proj['name']:info_for(proj) for proj in cfg['projects']}
    proj_names = build_proj_name_dictionary(proj_info)
    validate_dependency_versions(proj_info, proj_names)
    build_list = generate_build_list(proj_info, proj_names)
    for build_group in build_list:
        build_projects_in_group(proj_info, build_group)

def main(options, cfg):
    """Contains the main logic of the application. 'options' is the
    object returned by parse_command_line() and 'cfg' should be the
    object returned after parsing the yaml config file."""
    os.environ['JAVA_HOME'] = JAVA_HOME
    symlink_key_file(keyfile=options.keyfile)
    merge_and_tag(options, cfg)
    if options.build:
        build(cfg)

if __name__ == "__main__":
    options = parse_command_line()
    cfg = parse_yaml(yaml_path=options.config)
    main(options, cfg)
