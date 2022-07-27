Running RDFox and interacting with the endpoint
===============================================

If you want to run multiple queries or interact with RDFox while it is running, you can start the RDFox REST endpoint.

For example, if we have some RDF triples in `facts.ttl`, we can answer queries like this::

    input_files {
        "facts.ttl": "path/to/facts.ttl",
    }
    script = [
        'dstore create default type par-complex-nn',
        'import facts.ttl',
        'endpoint start',
    ]
    with RDFoxRunner(input_files, script) as rdfox:
        result = rdfox.query(sparql_query)

See the :class:`rdfox_runner.RDFoxEndpoint` API documentation for details of the query methods.
