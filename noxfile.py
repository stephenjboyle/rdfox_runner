"""
Configure environments to test rdfox runner across multiple RDFox versions.
"""

import nox


@nox.session
@nox.parametrize('rdfox', ["5.6", "6.2"], ids=["rdfox56", "rdfox62"])
def tests(session, rdfox):
    session.install("pytest~=5.2")
    session.install(f"rdfox=={rdfox}")
    session.install("-e", ".")
    session.run("pytest", "tests", "--log-level=DEBUG", *session.posargs)
