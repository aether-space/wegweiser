# encoding: utf-8

"""
    Sphinx extension for autodocumenting a Pyramid app's routes.

    :copyright: Copyright (c) 2012 Andreas Stührk <andy-python@hammerhartes.de>
"""

import collections
import json
import os
import subprocess
import sys
from functools import partial

from docutils import nodes, statemachine
from docutils.parsers.rst import Directive, directives
from sphinx.ext.autodoc import AutodocReporter
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.nodes import nested_parse_with_titles


def get_routes(config, prefix=None, group_by=None):
    """Executes the helper script that extracts the routes out of the
    pyramid app."""
    python = sys.executable
    script = os.path.join(os.path.dirname(__file__), "extract.py")
    config = os.path.expanduser(config)
    args = [python, script, config]
    if group_by:
        args.append("--group=" + group_by)
    if prefix:
        args.append("--prefix=" + prefix)
    p = subprocess.Popen(args=args, stdout=subprocess.PIPE)
    (stdout, _) = p.communicate()
    return json.loads(stdout.decode("utf-8"))


class _PyramidDirective(Directive):
    def _prepare_env(self):
        env = self.state.document.settings.env
        if not hasattr(env, "pyramid_routes"):
            # Mapping docname => list of view source files
            env.pyramid_routes = collections.defaultdict(set)

    def _get_routes(self, prefix=None, group_by=None):
        config = self.state.document.settings.env.app.config
        return get_routes(
            config.wegweiser["app_config"], prefix=prefix, group_by=group_by)

    def _render_route(self, route):
        env = self.state.document.settings.env
        if route["doc"]:
            env.pyramid_routes[env.docname].add(route["doc"][0])
        route_id = "route-{0}".format(env.new_serialno("route"))
        route_node = nodes.section(ids=[route_id])
        route_node += nodes.title(text=self._strip_prefix(route["pattern"]))
        route_node += self._render_request_methods(route)
        route_node += self._render_response(route)
        if route["doc"] is not None:
            self._render_docstring(route_node, *route["doc"])
        return route_node

    def _get_request_methods(self, route):
        for (name, value) in route["predicates"]:
            if name == "RequestMethodPredicate":
                return value
        return []

    def _render_request_methods(self, route):
        request_methods = self._get_request_methods(route)
        if request_methods:
            node = nodes.paragraph()
            node += nodes.strong(text="Request methods: ")
            for (i, method) in enumerate(request_methods):
                if i >= 1:
                    node += nodes.inline(text=", ")
                node += nodes.literal(text=method)
            node += nodes.Text("\n")
            return node
        return []

    def _render_response(self, route):
        if route["renderer"]:
            node = nodes.paragraph()
            node += nodes.strong(text="Response: ")
            node += nodes.inline(text=route["renderer"])
            return node

    def _render_docstring(self, node, filename, start_offset, docstring):
        """
        Renders a docstring (which should contain reStructuredText).

        :param node: Parent node to which the docstring's content should be
        added.
        :param str filename: Docstring's source filename.
        :param int start_offset: Number of line where the docstring begins.
        :param str docstring: The docstring itself.
        """
        content = statemachine.ViewList()
        docstring = prepare_docstring(docstring)
        for (i, line) in enumerate(docstring, start_offset):
            content.append(line, filename, i)
        old_reporter = self.state.memo.reporter
        self.state.memo.reporter = AutodocReporter(content, old_reporter)
        nested_parse_with_titles(self.state, content, node)
        self.state.memo.reporter = old_reporter

    def _strip_prefix(self, pattern):
        """Strips the prefix set in the directive's options from the given
        route pattern.
        """
        prefix = self.options.get("prefix")
        if prefix and pattern.startswith(prefix):
            pattern = pattern[len(prefix) - prefix.endswith("/"):]
        return pattern


class PyramidRouteDirective(_PyramidDirective):
    "Document a single Pyramid route."

    has_content = True
    required_arguments = 1

    def run(self):
        self._prepare_env()
        routes = dict((r["name"], r) for r in self._get_routes())
        return [self._render_route(routes[self.arguments[0]])]


class _GroupRendererRegistry(object):
    def __init__(self):
        self.renderers = {}

    def __call__(self, name):
        def decorator(f):
            self.renderers[name] = f
            return f
        return decorator

    def __getitem__(self, item):
        return self.renderers[item]

class PyramidRoutesDirective(_PyramidDirective):
    """Document all Pyramid routes.

    Usage::

       .. pyramidroutes::
          :prefix: /example
    """

    group_renderer = _GroupRendererRegistry()

    option_spec = {
        "prefix": directives.unchanged,
        "groupby": partial(directives.choice, values=["module"])
    }

    def run(self):
        self._prepare_env()
        group_by = self.options.get("groupby", "")
        prefix = self.options.get("prefix")
        routes = self._get_routes(prefix=prefix, group_by=group_by)
        try:
            renderer = self.group_renderer[group_by]
        except KeyError:
            raise self.error("Invalid group: {0!r}".format(group_by))
        else:
            return renderer(self, routes)

    @group_renderer("")
    def _default_group_renderer(self, routes):
        return [self._render_route(route) for route in routes]

    @group_renderer("module")
    def _module_group_renderer(self, modules):
        result = []
        env = self.state.document.settings.env
        for (name, module) in modules.items():
            node_id = "module-" + name
            node = nodes.section(ids=[node_id])
            result.append(node)
            node += nodes.title(text=name)
            if module["doc"]:
                self._render_docstring(node, *module["doc"])
                env.pyramid_routes[env.docname].add(module["doc"][0])
            for route in module["routes"]:
                node += self._render_route(route)
        return result


def get_outdated_documents(app, env, added, changed, removed):
    changed = []
    if hasattr(env, "pyramid_routes"):
        for (document, source_files) in env.pyramid_routes.items():
            for filename in source_files:
                mtime = os.path.getmtime(filename)
                if mtime > env.all_docs[document]:
                    changed.append(document)
                    break
    return changed

def purge_pyramid_routes(app, env, docname):
    if hasattr(env, "pyramid_routes"):
        if docname in env.pyramid_routes:
            del env.pyramid_routes[docname]

def setup(app):
    app.add_directive("pyramidroute", PyramidRouteDirective)
    app.add_directive("pyramidroutes", PyramidRoutesDirective)
    app.add_config_value("wegweiser", {}, "env")
    app.connect("env-get-outdated", get_outdated_documents)
    app.connect("env-purge-doc", purge_pyramid_routes)
