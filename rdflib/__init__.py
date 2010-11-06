"""\
A pure Python package providing the core RDF constructs.

The packages is intended to provide the core RDF types and interfaces
for working with RDF. The package defines a plugin interface for
parsers, stores, and serializers that other packages can use to
implement parsers, stores, and serializers that will plug into the
rdflib package.

The primary interface `rdflib` exposes to work with RDF is
`rdflib.graph.Graph`.

A tiny example:

    >>> import rdflib

    >>> g = rdflib.Graph()
    >>> result = g.parse("http://eikeon.com/foaf.rdf")

    >>> print "graph has %s statements." % len(g)
    graph has 34 statements.
    >>>
    >>> for s, p, o in g:
    ...     if (s, p, o) not in g:
    ...         raise Exception("It better be!")

    >>> s = g.serialize(format='n3')

"""
__docformat__ = "restructuredtext en"

__version__ = "2.5.0"
__date__ = "not/yet/released"

import sys
# generator expressions require 2.4
assert sys.version_info >= (2,4,0), "rdflib requires Python 2.4 or higher"
del sys

import logging
_logger = logging.getLogger("rdflib")
_logger.info("version: %s" % __version__)


from rdflib.term import URIRef, BNode, Literal

from rdflib.graph import Graph, ConjunctiveGraph

from rdflib.namespace import Namespace

from rdflib.syntax.parsers import Parser
