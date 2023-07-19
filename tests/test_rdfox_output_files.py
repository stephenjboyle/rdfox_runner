# -*- coding: utf-8 -*-

import pytest

from pathlib import Path
from io import StringIO
import shutil
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, FOAF
import requests

from rdfox_runner.run_rdfox import RDFoxRunner, run_rdfox_collecting_output
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


@pytest.fixture
def script(setup_script):
    return setup_script + [
        'import facts.ttl',
        'set query.answer-format "text/csv"',
        'set output "output.csv"',
        'answer query.rq',
        'quit',
    ]


# It's important this is a fixture not a constant, because the StringIO needs
# resetting.
@pytest.fixture
def input_files():
    return {
        "facts.ttl": HERE / "w3c_example.ttl",
        "query.rq": StringIO("""
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT ?person WHERE {
                <http://example.org/bob#me> foaf:knows ?person
            }
            """),
    }


def test_static_output(input_files, script):
    runner = RDFoxRunner(input_files, script)
    with runner:
        result = runner.files("output.csv").read_text()

    assert result == "person\nhttp://example.org/alice#me\n"


def test_static_output_copy(input_files, tmp_path, script):
    output_path = tmp_path / "output/output.csv"
    output_path.parent.mkdir()
    working_dir = tmp_path / "working"
    runner = RDFoxRunner(input_files, script, working_dir=working_dir)
    with runner:
        shutil.copy(runner.files("output.csv"), output_path)

    assert output_path.read_text() == "person\nhttp://example.org/alice#me\n"


def test_static_output_helper(input_files, script):
    output_files = {
        "friends": "output.csv",
    }
    result = run_rdfox_collecting_output(input_files, script, output_files)
    assert result == {
        "friends": "person\nhttp://example.org/alice#me\n",
    }
