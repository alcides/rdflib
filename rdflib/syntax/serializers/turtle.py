"""
Turtle RDF graph serializer for RDFLib.
See <http://www.w3.org/TeamSubmission/turtle/> for syntax specification.
"""
from rdflib.term import BNode, Literal, URIRef

from rdflib.syntax.serializers.RecursiveSerializer import RecursiveSerializer
from rdflib.exceptions import Error

from rdflib.namespace import RDF


SUBJECT = 0
VERB = 1
OBJECT = 2

_GEN_QNAME_FOR_DT = False
_SPACIOUS_OUTPUT = False


class TurtleSerializer(RecursiveSerializer):

    short_name = "turtle"
    indentString = '    '

    def __init__(self, store):
        super(TurtleSerializer, self).__init__(store)
        self.keywords = {
            RDF.type: 'a'
        }
        self.reset()
        self.stream = None
        self._spacious = _SPACIOUS_OUTPUT

    def reset(self):
        super(TurtleSerializer, self).reset()
        self._shortNames = {}
        self._started = False

    def serialize(self, stream, base=None, encoding=None, spacious=None, **args):
        self.reset()
        self.stream = stream
        self.base = base

        if spacious is not None:
            self._spacious = spacious
        # In newer rdflibs these are always in the namespace manager
        #self.store.prefix_mapping('rdf', RDFNS)
        #self.store.prefix_mapping('rdfs', RDFSNS)

        self.preprocess()
        subjects_list = self.orderSubjects()

        self.startDocument()

        firstTime = True
        for subject in subjects_list:
            if self.isDone(subject):
                continue
            if firstTime:
                firstTime = False
            if self.statement(subject) and not firstTime:
                self.write('\n')

        self.endDocument()
        stream.write("\n")

    def preprocessTriple(self, triple):
        super(TurtleSerializer, self).preprocessTriple(triple)
        for i, node in enumerate(triple):
            if node in self.keywords:
                continue
            # Don't use generated prefixes for subjects and objects
            self.getQName(node, gen_prefix=(i==1))
            if isinstance(node, Literal) and node.datatype:
                self.getQName(node.datatype, gen_prefix=_GEN_QNAME_FOR_DT)
        p = triple[1]
        if isinstance(p, BNode):
            self._references[p] = self.refCount(p) + 1

    def getQName(self, uri, gen_prefix=True):
        if not isinstance(uri, URIRef):
            return None
        try:
            parts = self.store.compute_qname(uri)
        except Exception, e:
            pfx = self.store.store.prefix(uri)
            if pfx is not None:
                parts = (pfx, uri, '')
            else:
                parts = None
        if parts:
            prefix, namespace, local = parts
            if not gen_prefix and prefix.startswith('_'):
                return None
            # Local parts with '.' will mess up serialization
            if '.' in local:
                return None
            self.addNamespace(prefix, namespace)
            return u'%s:%s' % (prefix, local)
        else:
            return None
        #if self.base and uri.startswith(self.base):
        #    # this feels too simple, should it work?
        #    return '<%s>'%uri[len(self.base):]

    def startDocument(self):
        self._started = True
        ns_list = sorted(self.namespaces.items())
        for prefix, uri in ns_list:
            self.write(self.indent()+'@prefix %s: <%s> .\n' % (prefix, uri))
        if ns_list and self._spacious:
            self.write('\n')

    def endDocument(self):
        if self._spacious:
            self.write('\n')

    def statement(self, subject):
        self.subjectDone(subject)
        return self.s_squared(subject) or self.s_default(subject)

    def s_default(self, subject):
        self.write('\n'+self.indent())
        self.path(subject, SUBJECT)
        self.predicateList(subject)
        self.write(' .')
        return True

    def s_squared(self, subject):
        if (self.refCount(subject) > 0) or not isinstance(subject, BNode):
            return False
        self.write('\n'+self.indent()+'[]')
        #self.depth+=1
        self.predicateList(subject)
        #self.depth-=1
        self.write(' .')
        return True

    def path(self, node, position, newline=False):
        if not (self.p_squared(node, position, newline)
                or self.p_default(node, position, newline)):
            raise Error("Cannot serialize node '%s'"%(node, ))

    def p_default(self, node, position, newline=False):
        if position != SUBJECT and not newline:
            self.write(' ')
        self.write(self.label(node, position))
        return True

    def label(self, node, position):
        if node == RDF.nil:
            return '()'
        if position is VERB and node in self.keywords:
            return self.keywords[node]
        if isinstance(node, Literal):
            return node._literal_n3(use_plain=True,
                    qname_callback=lambda dt:
                            self.getQName(dt, _GEN_QNAME_FOR_DT))
        else:
            return self.getQName(node, position==VERB) or node.n3()

    def p_squared(self, node, position, newline=False):
        if (not isinstance(node, BNode)
            or node in self._serialized
            or self.refCount(node) > 1
            or position == SUBJECT):
            return False

        if not newline:
            self.write(' ')

        if self.isValidList(node):
            # this is a list
            self.write('(')
            self.depth += 1#2
            self.doList(node)
            self.depth -= 1#2
            self.write(' )')
        else:
            self.subjectDone(node)
            self.depth += 2
            #self.write('[\n' + self.indent())
            self.write('[')
            self.depth -= 1
            #self.predicateList(node, newline=True)
            self.predicateList(node, newline=False)
            #self.write('\n' + self.indent() + ']')
            self.write(' ]')
            self.depth -= 1

        return True

    def isValidList(self, l):
        """
        Checks if l is a valid RDF list, i.e. no nodes have other properties.
        """
        try:
            if not self.store.value(l, RDF.first):
                return False
        except:
            return False
        while l:
            if l != RDF.nil and len(
                    list(self.store.predicate_objects(l))) != 2:
                return False
            l = self.store.value(l, RDF.rest)
        return True

    def doList(self,l):
        while l:
            item = self.store.value(l, RDF.first)
            if item:
                self.path(item, OBJECT)
                self.subjectDone(l)
            l = self.store.value(l, RDF.rest)

    def predicateList(self, subject, newline=False):
        properties = self.buildPredicateHash(subject)
        propList = self.sortProperties(properties)
        if len(propList) == 0:
            return
        self.verb(propList[0], newline=newline)
        self.objectList(properties[propList[0]])
        for predicate in propList[1:]:
            self.write(';\n' + self.indent(1))
            self.verb(predicate, newline=True)
            self.objectList(properties[predicate])

    def verb(self, node, newline=False):
        self.path(node, VERB, newline)

    def objectList(self, objects):
        count = len(objects)
        if count == 0:
            return
        depthmod = (count == 1) and 0 or 1
        self.depth += depthmod
        self.path(objects[0], OBJECT)
        for obj in objects[1:]:
            self.write(',\n' + self.indent(1))
            self.path(obj, OBJECT, newline=True)
        self.depth -= depthmod


