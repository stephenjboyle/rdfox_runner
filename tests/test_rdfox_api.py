# -*- coding: utf-8 -*-

import pytest

from pathlib import Path
from io import StringIO
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, FOAF
import requests

from rdfox_runner.run_rdfox import RDFoxRunner
from rdfox_runner.rdfox_endpoint import ParsingError


HERE = Path(__file__).parent

QUERY_COUNT_FRIENDS = """
SELECT ?name (COUNT(?friend) AS ?count)
WHERE {
    ?person foaf:name ?name .
    ?person foaf:knows ?friend .
}
GROUP BY ?person ?name
ORDER BY ?person
"""


@pytest.fixture(scope="module")
def rdfox():
    input_files = {
        "facts.ttl": HERE / "w3c_example.ttl",
    }
    script = [
        'dstore create default par-complex-nn',
        'import facts.ttl',
        'set endpoint.port "12111"',
        'endpoint start',
    ]
    # Namespaces available in queries
    namespaces = {
        "foaf": FOAF,
    }
    with RDFoxRunner(input_files, script, namespaces) as rdfox:
        yield rdfox


def test_query(rdfox):
    result = rdfox.query(QUERY_COUNT_FRIENDS)
    assert list(result) == [
        (Literal("Alice"), Literal(3)),
        (Literal("Bob"), Literal(1)),
        (Literal("Charlie"), Literal(1)),
    ]


def test_query_records(rdfox):
    result = rdfox.query_records(QUERY_COUNT_FRIENDS)
    assert list(result) == [
        {"name": "Alice", "count": 3},
        {"name": "Bob", "count": 1},
        {"name": "Charlie", "count": 1},
    ]


def test_query_records_returns_urifrefs(rdfox):
    query = """
    SELECT ?person WHERE {
        <http://example.org/bob#me> foaf:knows ?person
    }
    """
    result = rdfox.query_records(query)
    assert list(result) == [
        {"person": URIRef("http://example.org/alice#me")},
    ]


def test_rdfox_error_for_missing_file(caplog):
    input_files = {}
    script = [
        'dstore create default par-complex-nn',
        'import facts_does_not_exist.ttl',
        'quit',
    ]
    with RDFoxRunner(input_files, script) as rdfox:
        pass

    assert "File with name 'facts_does_not_exist.ttl' cannot be found." in caplog.text


def test_rdfox_error_for_bad_query(rdfox):
    query = "SELECT ?person WHERE"
    with pytest.raises(ParsingError, match="'{' expected"):
        rdfox.query(query)
