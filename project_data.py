#!/usr/bin/env python

import edn_format
import pprint

def slurp(filename):
    with open(filename, 'r') as f:
        return f.read()

class ProjectDataException(Exception):
    """Base class for project data exceptions."""
    pass

class InvalidLeinProjectException(ProjectDataException):
    """Thrown when an invalid leiningen project file is detected."""
    pass

class DependenciesNotFoundException(ProjectDataException):
    """Thrown when no dependencies are found in a project file."""
    pass

class Dependency(object):
    def __init__(self, group_id, artifact_id, version):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version

    def __str__(self):
        return str(
            {   'group_id': self.group_id,
                'artifact_id': self.artifact_id,
                'version': self.version
            }
        )

class ProjectData(object):
    def __init__(self, group_id, artifact_id, version, dependencies):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.dependencies = dependencies

    def __str__(self):
        return str(
            {   'group_id': self.group_id,
                'artifact_id': self.artifact_id,
                'version': self.version,
                'dependencies': [ str(dep) for dep in self.dependencies ]
            }
        )

class LeinProjectData(ProjectData):
    def parse_descriptor(self, descriptor):
        elms = str.split(str(descriptor), "/", 2)
        if len(elms) == 1:
            return elms[0], elms[0]
        else:
            return elms[0], elms[1]

    def find_dependencies(self, data):
        for i in range(0, len(data) - 1):
            if str(data[i]) == ":dependencies":
                return data[i + 1]
        raise DependenciesNotFoundException()

    def project_data_from_desc(self, dep):
        (group_id, artifact_id) = self.parse_descriptor(dep[0])
        version = dep[1]
        return Dependency(group_id, artifact_id, version)

    def extract_dependencies(self, data):
        return [
            self.project_data_from_desc(dep)
            for dep in self.find_dependencies(data)
        ]

    def __init__(self, filename):
        data = edn_format.loads(slurp(filename))
        if (str(data[0]) != "defproject"):
            raise InvalidLeinProjectException()
        (self.group_id, self.artifact_id) = self.parse_descriptor(data[1])
        self.version = data[2]
        self.dependencies = self.extract_dependencies(data)

pd = LeinProjectData("/Users/dennis/src/iplant/ua/heuristomancer/project.clj")
print pd
