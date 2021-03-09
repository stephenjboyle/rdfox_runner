# -*- coding: utf-8 -*-

import pytest

from rdfox_runner import run_rdfox


@pytest.fixture
def test_files(tmp_path):
    # Set up test files
    with open(tmp_path / "facts.ttl", "wt") as f:
        f.write("""
PREFIX : <https://ukfires.org/probs/ontology/>
:Farming a :Process .
""")
    with open(tmp_path / "query.rq", "wt") as f:
        f.write("SELECT ?s ?p ?o WHERE { ?s ?p ?o }\n")
    return tmp_path


def test_simple_run(test_files):
    input_files = {
        "facts.ttl": test_files / "facts.ttl",
        "query.rq": test_files / "query.rq",
    }
    output_files = {
        "result": "answer.csv",
    }
    script = [
        'dstore create default par-complex-nn',
        'import facts.ttl',
        'set query.answer-format "text/csv"',
        'set output "answer.csv"',
        'answer query.rq',
    ]
    result = run_rdfox(input_files, output_files, script)

    assert result == {
        "result": ("s,p,o\n"
                   "https://ukfires.org/probs/ontology/Farming,"
                   "http://www.w3.org/1999/02/22-rdf-syntax-ns#type,"
                   "https://ukfires.org/probs/ontology/Process\n")
    }


def test_rdfox_error(caplog):
    input_files = {}
    output_files = {}
    script = [
        'dstore create default par-complex-nn',
        'import facts_does_not_exist.ttl',
    ]
    run_rdfox(input_files, output_files, script)

    assert "File with name 'facts_does_not_exist.ttl' cannot be found." in caplog.text
