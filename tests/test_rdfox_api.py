# -*- coding: utf-8 -*-

import pytest

from pathlib import Path
from io import StringIO
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, FOAF
import requests
from packaging.version import Version

from rdfox_runner.run_rdfox import RDFoxRunner, RDFoxVersionError, get_rdfox_version, check_rdfox_version
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


def test_query_records_n3_format(rdfox):
    query = """
    SELECT ?rel WHERE {
        <http://example.org/bob#me> ?rel <http://example.org/alice#me>
    }
    """
    result = rdfox.query_records(query, n3=True)
    assert list(result) == [{"rel": "foaf:knows"}]


def test_rdfox_error_for_missing_file(caplog):
    input_files = {}
    script = [
        'dstore create default par-complex-nn',
        'import facts_does_not_exist.ttl',
        'quit',
    ]
    with RDFoxRunner(input_files, script):
        pass

    assert "File with name 'facts_does_not_exist.ttl' cannot be found." in caplog.text


@pytest.fixture
def bad_rdfox_licence():
    import os
    if "RDFOX_LICENSE_CONTENT" in os.environ:
        original_value = os.environ["RDFOX_LICENSE_CONTENT"]
        os.environ["RDFOX_LICENSE_CONTENT"] = "bad licence"
        yield
        os.environ["RDFOX_LICENSE_CONTENT"] = original_value
    else:
        os.environ["RDFOX_LICENSE_CONTENT"] = "bad licence"
        yield
        del os.environ["RDFOX_LICENSE_CONTENT"]


def test_rdfox_critical_error_raises(bad_rdfox_licence):
    # Bad licence file causes a "critical error" which should be propagated up
    script = ['quit']
    with pytest.raises(Exception):
        with RDFoxRunner({}, script):
            pass


def test_rdfox_error_for_bad_query(rdfox):
    query = "SELECT ?person WHERE"
    with pytest.raises(ParsingError, match="'{' expected"):
        rdfox.query(query)


def test_add_triples(rdfox):
    bob_friends_1 = rdfox.query_records(QUERY_COUNT_FRIENDS)[1]["count"]
    assert bob_friends_1 == 1

    rdfox.add_triples([
        (URIRef("http://example.org/bob#me"), FOAF.knows, URIRef("http://example.org/mary#me")),
    ])
    print("facts")
    print(rdfox.facts())
    bob_friends_2 = rdfox.query_records(QUERY_COUNT_FRIENDS)[1]["count"]
    assert bob_friends_2 == 2


def test_get_rdfox_version():
    version = get_rdfox_version()
    assert isinstance(version, Version)


def test_check_max_version():
    # Assume the version we have isn't this old...
    with pytest.raises(RDFoxVersionError):
        check_rdfox_version("<= 0.1")
