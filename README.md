# RDFtoCSharp-ClassConverter
Python tool to generate C# classes from RDF ontology files

This tool reads an ontology file, such as one in `.ttl` format, and generates a corresponding C# file. Based on the ontology's defined classes, datatype properties, and enumerations, the tool replicates the class hierarchy, assigns the appropriate attributes to each class, and defines any enumerations present in the ontology. For all attributes JSON property names are defined to allow for exporting class instances to JSON.
