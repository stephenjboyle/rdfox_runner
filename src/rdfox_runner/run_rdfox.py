"""Functions for running RDFox with necessary input files and scripts, and
collecting results.

This aims to hide the complexity of setting up RDFox, loading data, adding
rules, answering queries, behind a simple function that maps data -> answers.
"""

import time
import logging
from io import StringIO
import re
from pathlib import Path

from typing import List, Union, Optional, Mapping

StrPath = Union[str, Path]

from .rdfox_endpoint import RDFoxEndpoint
from .command_runner import CommandRunner, PathOrIO

logger = logging.getLogger(__name__)


ERROR_PATTERN = re.compile(r"Error: .*|"
                           r"File with name '.*' cannot be found|"
                           r"An error occurred while executing the command:|"
                           r"The server could not start listening")

ENDPOINT_PATTERN = re.compile(r"The REST endpoint was successfully started at port number/service name (\S+)")


class RDFoxRunner(RDFoxEndpoint):
    """Context manager to run RDFox in a temporary directory.

    :param input_files: mapping of files {target path: source file} to set up in
        temporary working directory.
    :param script: RDFox commands to run, either as a list of strings or a
        single string.
    :param namespaces: dict of RDFlib namespaces to bind
    :param wait: whether to wait for RDFox to exit when starting.  If None, look
        for the presence of an "endpoint start" command in `script` and wait if
        not found.
    :param working_dir: Path to setup command in, defaults to a temporary
        directory
    :param rdfox_executable: Path RDFox executable (default "RDFox")
    """

    def __init__(
            self,
            input_files: Mapping[str, PathOrIO],
            script: Union[List[str], str],
            namespaces: Optional[Mapping] = None,
            wait: Union[bool, None] = None,
            working_dir: Optional[StrPath] = None,
            rdfox_executable: Optional[StrPath] = None,
    ):
        super().__init__(namespaces)

        MASTER_KEY = "__master.rdfox"
        if MASTER_KEY in input_files:
            raise ValueError(f'Cannot have an input file named "{MASTER_KEY}"')

        if not isinstance(script, str):
            script = "\n".join(script)

        if rdfox_executable is None:
            rdfox_executable = "RDFox"

        if wait is None:
            # Try to choose a good default
            if "endpoint start" in script:
                wait = False
            else:
                wait = True
        self.wait = wait

        # Generate the master script
        self.input_files = {
            **input_files,
            MASTER_KEY: StringIO(script),
        }
        self.command = [rdfox_executable, "sandbox", ".", f"exec {MASTER_KEY}"]
        self.working_dir = working_dir

    def _check_for_errors(self, line):
        match = ENDPOINT_PATTERN.match(line)
        if match:
            port = match.group(1)
            logger.info("RDFox started on port %s", port)
            self.connect("http://localhost:%s" % port)

        if ERROR_PATTERN.match(line):
            logger.error("RDFox error: %s" % line)
            # TODO often the error is more than one line -- should keep printing
            # while the next lines are indented.

    def start(self, wait_secs=None):
        """Start RDFox.

        :param wait_secs: how many seconds to wait for RDFox to start.
        """
        logger.debug("Starting to run RDFox")
        self._runner = CommandRunner(
            self.input_files,
            self.command,
            wait=self.wait,
            working_dir=self.working_dir,
            output_callback=self._check_for_errors,
        )
        self._runner.start()

        if wait_secs is not None:
            time.sleep(wait_secs)

    def stop(self):
        """Stop RDFox."""
        logger.debug("Stopping RDFox")
        self._runner.stop()

    def __enter__(self):
        self.start(wait_secs=0.5)
        return self

    def __exit__(self, exc, value, tb):
        self.stop()

    def files(self, path) -> Path:
        """Return path to temporary directory.

        :param path: path relative to the working directory
        """
        return self._runner.files(path)


def run_rdfox_collecting_output(input_files: Mapping[str, PathOrIO],
                                script: Union[List[str], str],
                                output_files: Mapping[str, str],
                                **kwargs) -> Mapping[str, str]:
    """Run RDFox once and return requested output files' contents.

    :param input_files: passed to :class:`RDFoxRunner`.
    :param script: passed to :class:`RDFoxRunner`.
    :param output_files: mapping of {key: filename} of files whose contents should be returned.
    :param \\**kwargs: passed to :class:`RDFoxRunner`.
    """

    if "wait" not in kwargs:
        kwargs["wait"] = True

    result = {}
    with RDFoxRunner(input_files, script, **kwargs) as rdfox:
        for key, filename in output_files.items():
            result[key] = rdfox.files(filename).read_text()
    return result
