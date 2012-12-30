# encoding: utf-8

"""
    Helper for Wegweiser: Tries to find the views for all routes and
    prints out a JSON serialized object with the route patterns as
    keys and the corresponding view as value.

    Example output (no grouping)::

       [
        {
         "name": "view_wiki",
         "predicates": [],
         "pattern": "/",
         "renderer": null,
         "module": "example.views",
         "doc": [
          "/home/andy/src/wegweiser/docs/example_app/example/views.py",
          6,
          "Redirect to the FrontPage wiki page."
         ]
        }
       ]

    :copyright: Copyright (c) 2012 Andreas Stührk <andy-python@hammerhartes.de>
"""

import argparse
import inspect
import json
import operator
import sys

from pyramid import interfaces, paster, traversal
from pyramid.request import Request
from zope.interface import providedBy


def find_view(registry, route):
    """Given a registry and a route, try to find the corresponding view
    callable.

    Limitations:

    - Does not support multi views.
    """
    root_factory = registry.queryUtility(
        interfaces.IRootFactory, default=traversal.DefaultRootFactory)
    request_iface = registry.queryUtility(
        interfaces.IRouteRequest, name=route.name, default=interfaces.IRequest)
    root_factory = route.factory or root_factory

    request_factory = registry.queryUtility(
        interfaces.IRequestFactory, default=Request)
    request = request_factory({})
    root = root_factory(request)

    # Find context
    traverser = registry.adapters.queryAdapter(root, interfaces.ITraverser)
    if traverser is None:
        traverser = traversal.ResourceTreeTraverser(root)
    tdict = traverser(request)
    context = tdict["context"]
    view_name = tdict["view_name"]

    # Find view callable
    context_iface = providedBy(context)
    view = registry.adapters.lookup(
        (interfaces.IViewClassifier, request_iface, context_iface),
        interfaces.IView, name=view_name, default=None)
    return view

def get_view_predicates(view):
    """Returns the given view's predicates as list with (predicate's class
    name, predicate's value) pairs as items. Assumes the predicate's
    value is stored an attribute ``val``.
    """
    predicates = []
    for predicate in getattr(view, "__predicates__", []):
        if hasattr(predicate, "val"):
            predicates.append((type(predicate).__name__, predicate.val))
    return predicates

def get_view_renderer(view):
    # This is one big hack: The renderer is stored as argument
    # "view_renderer" passed to
    # `pyramid.config.views.ViewDeriver._rendered_view` which returns
    # a wrapper whose name is "rendered_view"
    while (hasattr(view, "__wraps__") and
           (not hasattr(view, "__code__") or
            view.__code__.co_name != "rendered_view")):
        view = view.__wraps__
    if getattr(view, "__closure__", None) is not None:
        for (name, cell) in zip(view.__code__.co_freevars, view.__closure__):
            if name == "view_renderer":
                return cell.cell_contents

def _get_unwrapped(func):
    while True:
        if hasattr(func, "__wraps__"):
            func = func.__wraps__
        elif hasattr(func, "__wrapped__"):
            func = func.__wrapped__
        else:
            break
    return func

def get_docstring(func):
    """Returns a triplet (filename, lineno of docstring start, docstring)
    for the given object. If the object is a function and the function
    wraps another function, the unwrapped function is used.
    """
    func = _get_unwrapped(func)
    try:
        filename = inspect.getsourcefile(func)
    except TypeError:
        return None
    (lines, start_offset) = inspect.getsourcelines(func)
    # Unfortunately, `inspect-getsourcelines` always returns 0 as start_offset
    start_offset = max(start_offset, 1)
    for (lineno, line) in enumerate(lines, start_offset):
        if line.lstrip().startswith(('"', "'")):
            break
    else:
        return None
    docstring = inspect.getdoc(func)
    if docstring is not None:
        return (filename, lineno, docstring)
    return None

def collect(env):
    """Returns a list of routes, sorted by pattern. Each route is a dictionary
    with the following keys:

       * ``name``: The route's name
       * ``pattern``: The route's pattern
       * ``predicates``: A list of predicates associated with the route's view.
       * ``module``: The module in which the view connected with the route
         is defined.
       * ``doc``: The docstring of the view connected with the route (as
         returned by ``inspect.getdoc``) or ``None`` if no docstring could
         be found.
       * ``renderer``: The renderer that is used by the route's view.
    """
    routes = []
    mapper = env["registry"].queryUtility(interfaces.IRoutesMapper)
    root_factory = env["registry"].queryUtility(
        interfaces.IRootFactory, default=traversal.DefaultRootFactory)
    request_factory = env["registry"].queryUtility(
        interfaces.IRequestFactory, default=Request)
    request = request_factory({})
    root = root_factory(request)
    traverser = env["registry"].adapters.queryAdapter(root, interfaces.ITraverser)
    if traverser is None:
        traverser = traversal.ResourceTreeTraverser(root)

    for (name, route) in mapper.routes.items():
        view = find_view(env["registry"], route)
        renderer = get_view_renderer(view)
        predicates = get_view_predicates(view)
        pattern = route.pattern
        if not pattern.startswith("/"):
            pattern = "/" + pattern
        value = {
            "name": route.name,
            "pattern": pattern,
            "predicates": predicates,
            "module": inspect.getmodule(view).__name__,
            "doc": get_docstring(view),
            "renderer": None
        }
        if renderer is not None:
            value["renderer"] = renderer.name
        routes.append(value)
    return sorted(routes, key=operator.itemgetter("pattern"))

def group_by_modules(routes):
    grouped = {}
    for route in routes:
        name = route["module"]
        if name not in grouped:
            module = sys.modules[name]
            grouped[name] = {"doc": get_docstring(module), "routes": []}
        grouped[name]["routes"].append(route)
    return grouped


GROUP_FUNCS = {
    "module": group_by_modules
}

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--prefix")
    parser.add_argument("--group", choices=GROUP_FUNCS.keys())
    options = parser.parse_args(args)

    if options.group:
        group_func = GROUP_FUNCS[options.group]
    else:
        group_func = None

    env = paster.bootstrap(options.config)
    routes = collect(env)
    if options.prefix:
        routes = [r for r in routes if r["pattern"].startswith(options.prefix)]
    if group_func is not None:
        routes = group_func(routes)
    json.dump(routes, sys.stdout)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
