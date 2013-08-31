#!/usr/bin/env python

import re
import xml.etree.ElementTree as ET

from clojure.lang.fileseq import StringReader
from clojure.lang.cljkeyword import Keyword
from clojure.lang.lispreader import read
from clojure.lang.symbol import Symbol

def slurp(filename):
    with open(filename, 'r') as f:
        return f.read()

class ProjectDataException(Exception):
    """Base class for project data exceptions."""
    pass

class InvalidLeinProjectException(ProjectDataException):
    """Thrown when an invalid leiningen project file is detected."""
    pass

class InvalidLeinProjectDescriptor(ProjectDataException):
    """Thrown when a project descriptor is not a symbol."""
    pass

class InvalidLeinDependencyDescriptor(ProjectDataException):
    """Thrown when a dependency descriptor is not a symbol."""
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
    def __init__(self, group_id, artifact_id, version, dependencies,
                 validate_version, build, resolve_deps):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.dependencies = dependencies
        self.validate_version = validate_version
        self.build = build
        self.resolve_deps = resolve_deps

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

    def parse_project_descriptor(self, descriptor):
        if type(descriptor) != Symbol:
            raise InvalidLeinProjectDescriptor()
        return self.parse_descriptor(descriptor)

    def parse_dependency_descriptor(self, descriptor):
        if type(descriptor) != Symbol:
            raise InvalidLeinDependencyDescriptor()
        return self.parse_descriptor(descriptor)

    def find_dependencies(self, data):
        for i in range(0, len(data) - 1):
            if str(data[i]) == ":dependencies":
                return data[i + 1]
        raise DependenciesNotFoundException()

    def find_plugins(self, data):
        for i in range(0, len(data) - 1):
            if str(data[i]) == ":plugins":
                return data[i + 1]
        return []

    def project_data_from_desc(self, dep):
        (group_id, artifact_id) = self.parse_dependency_descriptor(dep[0])
        version = dep[1]
        return Dependency(group_id, artifact_id, version)

    def extract_dependencies(self, data):
        deps = [
            self.project_data_from_desc(dep)
            for dep in self.find_dependencies(data)
        ]
        deps += [
            self.project_data_from_desc(dep)
            for dep in self.find_plugins(data)
        ]
        return deps

    def __init__(self, filename, validate_version, build, resolve_deps):
        EOF = object()
        data = read(StringReader(slurp(filename)), False, EOF, True)
        if (type(data[0]) != Symbol or str(data[0]) != "defproject"):
            raise InvalidLeinProjectException()
        (group_id, artifact_id) = self.parse_project_descriptor(data[1])
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = data[2]
        self.validate_version = validate_version
        self.dependencies = self.extract_dependencies(data)
        self.build = build
        self.resolve_deps = resolve_deps

class MvnProjectData(ProjectData):
    ns_name = 'http://maven.apache.org/POM/4.0.0'
    ns_pattern = re.escape('{{{}}}'.format(ns_name))
    ns_regex = re.compile('^{}'.format(ns_pattern))

    def ns_tag(self, tag):
        return str(ET.QName(self.ns_name, tag))

    def tag_name(self, tag):
        return self.ns_regex.sub('', tag)

    def replace_prop_placeholders(self, props, text):
        return re.sub(
            r'\$\{([^\}]+)\}',
            lambda m: props[m.group(1)] if m.group(1) in props else m.group(0),
            text
        )

    def build_dependency(self, props, dep):
        group_id = self.replace_prop_placeholders(
            props, self.find_tag(dep, 'groupId').text
        )
        artifact_id = self.replace_prop_placeholders(
            props, self.find_tag(dep, 'artifactId').text
        )
        version = self.replace_prop_placeholders(
            props, self.find_tag(dep, 'version').text
        )
        return Dependency(group_id, artifact_id, version)

    def find_tag(self, xml, tag):
        return xml.find(self.ns_tag(tag))

    def get_project_properties(self, root):
        prop_elms = self.find_tag(root, 'properties')
        prop_elms = [] if prop_elms is None else prop_elms
        props = {
            self.tag_name(prop_elm.tag):prop_elm.text
            for prop_elm in prop_elms
        }
        props['project.groupId'] = self.replace_prop_placeholders(
            props, self.find_tag(root, 'groupId').text
        )
        props['project.artifactId'] = self.replace_prop_placeholders(
            props, self.find_tag(root, 'artifactId').text
        )
        props['project.version'] = self.replace_prop_placeholders(
            props, self.find_tag(root, 'version').text
        )
        return props

    def __init__(self, filename, validate_version, build, resolve_deps):
        tree = ET.parse(filename)
        root = tree.getroot()
        props = self.get_project_properties(root)
        self.group_id = props['project.groupId']
        self.artifact_id = props['project.artifactId']
        self.version = props['project.version']
        self.validate_version = validate_version
        self.dependencies = [
            self.build_dependency(props, dep)
            for dep in self.find_tag(root, 'dependencies')
        ]
        self.build = build
        self.resolve_deps = resolve_deps
        parent_pom = self.find_tag(root, 'parent')
        if parent_pom is not None:
            self.dependencies.append(self.build_dependency(props, parent_pom))
