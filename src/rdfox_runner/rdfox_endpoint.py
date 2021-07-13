"""Functions for running RDFox with necessary input files and scripts, and
collecting results.

This aims to hide the complexity of setting up RDFox, loading data, adding
rules, answering queries, behind a simple function that maps data -> answers.
"""

import logging
import re
import requests
from textwrap import indent
from rdflib import Graph, Literal

# Pandas is optional, but convenient if available
try:
    import pandas as pd
except ImportError:
    pd = None

from typing import List, Dict, Any, Optional, Mapping

logger = logging.getLogger(__name__)


ERROR_PATTERN = re.compile(r"Error: .*|"
                           r"File with name '.*' cannot be found|"
                           r"An error occurred while executing the command:|"
                           r"The server could not start listening")

ENDPOINT_PATTERN = re.compile(r"The REST endpoint was successfully started at port number/service name (\S+)")


class Error(Exception):
    """Base class for exceptions from this module."""
    pass


class ParsingError(Error):
    """Exception raised when RDFox returns a ParsingException.

    :param query: query the error refers to
    :param message: explanation of the error
    """
    def __init__(self, query, message):
        self.query = query
        self.message = message

    def __str__(self):
        return f"ParsingError: {self.message}"


class RDFoxEndpoint:
    """Interface to interact with a running RDFox endpoint.

    :param namespaces: dict of RDFlib namespaces to bind
    """

    def __init__(self, namespaces: Optional[Mapping] = None):
        self.namespaces = namespaces or {}
        self.server = None
        self.datastore = None
        self.graph = Graph("SPARQLUpdateStore", identifier="http://oxfordsemantic.tech/RDFox#DefaultTriples")
        for k, v in self.namespaces.items():
            self.graph.bind(k, v)

    def connect(self, url: str):
        """Connect to RDFox at given base URL.

        The SPARQL endpoint is at `{url}/datastores/default/sparql`.

        """
        self.server = url
        ENDPOINT = f"{url}/datastores/default/sparql"
        self.graph.open((ENDPOINT, ENDPOINT))

    def query(self, query_object, *args, **kwargs):
        """Query the SPARQL endpoint.

        This method is a simple wrapper about :meth:`rdflib.Graph.query` which
        shows more useful error output when there is a problem with the
        query.

        :raises: ParsingError
        """
        logger.debug("Sending query: %s", query_object)
        try:
            result = self.graph.query(query_object, *args, **kwargs)
            logger.debug("Query result: %s", result.bindings)
            return result

        except requests.HTTPError as err:
            logger.error("Query error: %s", err)
            logger.error(indent(err.response.content.decode(), "    "))
            if "ParsingException" in err.response.text:
                import urllib.parse
                qs = urllib.parse.urlparse(err.request.url).query
                full_query = urllib.parse.parse_qs(qs)["query"][0]
                logger.error("Query:")
                for i, line in enumerate(full_query.splitlines()):
                    logger.error(f"Line {i+1}: {line}")
                raise ParsingError(query=full_query, message=err.response.text)
            raise

    def query_dataframe(self, query_object, *args, **kwargs):
        """Query the SPARQL endpoint, returning a pandas DataFrame.

        See :meth:`query`.

        """
        if pd is None:
            raise RuntimeError("pandas is not available")
        res = self.query(query_object, *args, **kwargs)
        return pd.DataFrame(res, columns=[str(c) for c in res.vars])

    def query_records(self, query_object, *args, **kwargs) -> List[Dict[str, Any]]:
        """Query the SPARQL endpoint, returning a list of dicts.

        See :meth:`query`.

        """
        res = self.query(query_object, *args, **kwargs)
        return [
            {str(c): (value.value if isinstance(value, Literal) else value) for c, value in zip(res.vars, row)}
            for row in res
        ]

    def facts(self, format="text/turtle") -> str:
        """Fetch all facts from the server.

        :param format: format for results send in Accept header.

        """
        if self.server is None:
            raise RuntimeError("Need to connect to server first")
        response = requests.get(
            f"{self.server}/datastores/default/content",
            params={"fact-domain": "IDB"},
            headers={"accept": format},
        )
        logger.debug("Store contents response [%s]: %s", response.status_code, response.text)
        assert_reponse_ok(response, "Failed to retrieve facts.")
        return response.text

    def add_triples(self, triples):
        """Add triples to the RDF data store.

        In principle this should work via the rdflib SPARQLUpdateStore, but
        RDFox does not accept data in that format.

        Note: compatible with RDFox version 5.0 and later.

        """
        if self.server is None:
            raise RuntimeError("Need to connect to server first")
        triples = ["%s %s %s ." % (s.n3(), p.n3(), o.n3()) for s, p, o in triples]
        response = requests.patch(
            f"{self.server}/datastores/default/content",
            params={"operation": "add-content"},
            # Before RDFox version 5.0 it was {"mode": "add"}
            data="\n".join(triples),
        )
        response.raise_for_status()
        return response


def assert_reponse_ok(response, message):
    """Helper function to raise exception if the REST endpoint returns an unexpected
    status code.
    """
    if not response.ok:
        logger.error("Error answering query: %s", response.text)
        raise Exception(
            message
            + "\nStatus received={}\n{}".format(response.status_code, response.text)
        )
