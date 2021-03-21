Running basic RDFox scripts
===========================

The simplest way to use rdfox_runner goes like this:

- Set up a temporary directory with the required input files, scripts, rules etc.
- Run RDFox sandbox in that directory
- RDFox produces some output files
- The contents of the output files is captured and returned

For example, if we have some RDF triples in `facts.ttl`, and a query to answer in `query.rq`, we can get the answer to the query like this::

    input_files {
        "facts.ttl": "path/to/facts.ttl",
        "query.rq": "path/to/query.rq",
    }
    script = [
        'dstore create default par-complex-nn',
        'import facts.ttl',
        'set query.answer-format "text/csv"',
        'set output "output.csv"',
        'answer query.rq',
    ]
    with RDFoxRunner(input_files, script) as rdfox:
        result = rdfox.files("output.csv").read_text()

Alternatively, you can start RDFox running and then interact with its REST API; see :doc:`using_endpoint`.
