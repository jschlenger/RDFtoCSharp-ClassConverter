from array import typecodes
import rdflib
from rdflib.namespace import RDF, RDFS, OWL

# new class for class hierarchy
class element:
    def __init__(self, name, parent, leaf, attributes, allAttributes):
        self.name = name
        self.parent = parent
        self.leaf = leaf
        self.attributes = attributes # excludes inherited attributes
        self.allAttributes = allAttributes # includes inherited attributes

# conversion table for data types
# left side: data types originating from xsd and geosparql
# right side: corresponding C# data types
# this list should be extended according to personal needs
dataTypeConversion = {
    "string": "string",
    "integer": "int",
    "dateTime": "DateTime",
    "boolean": "bool",
    "wktLiteral": "string",
    "double": "double"
}

# function to deal separately with hash and slash namespaces
# example hash namespace: http://www.w3.org/2004/02/skos/core#Concept
# example slash namespace: http://xmlns.com/foaf/0.1/Person
def getName(iri):
    if "#" in iri:
        return iri.partition('#')[2]
    elif "/" in iri:
        lastSlash = iri.rfind("/")
        return iri[lastSlash+1:]
    else:
        return iri

# create new rdf graph
graph = rdflib.Graph()

# create and open new .cs file 
f = open("schema.cs", "w+")
f.write("using System;\n")
f.write("using Newtonsoft.Json;\n\n")
f.write("namespace MyNamespace\n")
f.write("{\n")

# in ontologies "Thing" is the parent class of every other class 
# write Thing class to C# file
f.write("\tpublic class Thing \n")
f.write("\t{\n")
f.write("\t}\n")

# read ontology file
ontologyFileName = 'ontology.ttl'
format_ = rdflib.util.guess_format(ontologyFileName)
graph.parse(ontologyFileName, format=format_)

# get all classes
classes = set()
for s , p in graph.subject_predicates(OWL.Class):
    if s[0:4] == "http":
        if "Type" not in s: # skip type classes (it is assumed that classes that are used to defined enumerations with the help of owl:NamedIndividual have a name that ends with "Type", e.g. SequenceType)
            classes.add(s)

# sort classes alphabetically (iri)
classes = sorted(classes)

# create "element" instances for them with parent, etc.
elements = set()
for elem in classes:
    node = element("", "", True, set(), set())
    node.name = elem
    for s, o in graph.subject_objects(RDFS.subClassOf):
        if s == elem:
            node.parent = o 
    if (None, RDFS.subClassOf, elem) in graph:
        node.leaf = False
    elements.add(node)

# find attributes for classes
for item in iter(elements):
    currentClass = item
    stop = True
    firstRun = True
    # attributes of parent classes also need to be included
    while stop:
        # find all attributes
        attrAndRel = set()
        for s in graph.subjects(RDFS.domain, currentClass.name):
            attrAndRel.add(s)

        # add attributes coming from unions (e.g. when the domain of a attribute includes a list of possible classes)
        rests = set()
        for s in graph.subjects(RDF.first, currentClass.name):
            if s == getName(s):
                rests.add(s)

        for rest in rests:
            unionStart = False
            remainder = rest
            while not unionStart:
                unionStart = True
                for s in graph.subjects(RDF.rest, remainder):
                    remainder = s
                    unionStart = False
            union = ""
            for s in graph.subjects(OWL.unionOf, remainder):
                union = s
            for domain in graph.subjects(RDFS.domain, union):
                attrAndRel.add(domain)              

        # sort out relationships (except from type relationships)
        for edge in attrAndRel:
            for o in graph.objects(edge, RDF.type):
                if o == OWL.DatatypeProperty:  # if "XMLSchema" in o (object) or "wktLiteral" in o (object):
                    if firstRun:
                        item.attributes.add(edge)
                    item.allAttributes.add(edge)
        
        # change current class of interest to parent class to search for inherited attributes
        if currentClass.parent == "":
            stop = False
            break
        else:
            for possibleParent in iter(elements):
                if getattr(possibleParent, "name") == currentClass.parent:
                    currentClass = possibleParent
                    firstRun = False
                    break          
                
# sort attributes alphabetically (iri) to make sure that the .cs file has the same order every time
for elem in iter(elements):
    sortedAttr = set()
    for attr in elem.attributes:
        sortedAttr.add(attr)
    elem.attributes = sorted(sortedAttr)
    sortedAllAttr = set()
    for attr in elem.allAttributes:
        sortedAllAttr.add(attr)
    elem.allAttributes = sorted(sortedAllAttr)

# find type classes (used for enumerations)
# a parent class for all enumerations was defined in the used ontology
# the URIref needs to be replaced accordingly
typeClasses = set()
for s in graph.subjects(RDFS.subClassOf, rdflib.URIRef("https://dtc-ontology.cms.ed.tum.de/ontology#Type")):
    typeClasses.add(s)

# write classes into C# file
for elem in iter(elements):
    f.write("\n")
    # class name and inheritance
    f.write("\tpublic class ")

    if elem.parent == "":
       f.write("{}".format(getName(elem.name)))
       f.write(" : Thing\n") # should be added to element.parent
    else:
       f.write("{}".format(getName(elem.name)))
       f.write(" : {}\n".format(getName(elem.parent)))

    f.write("\t{\n\n")

    # attributes
    for att in elem.attributes:
        type = "None"
        for o in graph.objects(att, RDFS.range):
            type = o.partition('#')[2]
        f.write("\t\t[JsonProperty(PropertyName = \"{}\")]\n".format(att))
        if "Type" in att: # not optimal to hard code this
            f.write("\t\tpublic string ")
        else:
            f.write("\t\tpublic {} ".format(dataTypeConversion.get(type)))
        f.write("_{} ".format(getName(att)))
        f.write("{ get; set; }\n\n")

    f.write("\t}")
    f.write("\n")

# add type classes (used for enumerations)
# enumerations are defined in as public static classes with readonly strings, in this way the IRIs of the individuals can be properly accessed (since special characters are not allowed in C# enums)
for typeClass in typeClasses:
    f.write("\n")
    f.write("\tpublic static class ")
    f.write("{}".format(getName(typeClass)))
    f.write("\n")
    f.write("\t{\n\n")
    
    for individual in graph.subjects(RDF.type, typeClass):
        f.write("\t\tpublic static readonly string ")
        f.write("{}".format(getName(individual)))
        f.write(" = \"")
        f.write("{}".format(individual))
        f.write("\";")
        f.write("\n")
    
    f.write("\n")
    f.write("\t}")
    f.write("\n")

f.write("\n}")
f.close()

# things to look out for that can cause issues:
# names of ontology classes should not coincide with class names used by the C# standard library (e.g. Object, Task, Assembly, Exception, etc.)
# in ontologies the names of individuals can start with numbers, such individuals are currently not covered by this python script
# only concepts that are explicitly defined in the ontology file are considered, other ontologies that are only integrated with an import statement might caused issues
# to solve this problem all imported ontologies should be copy pasted directly into the .ttl file