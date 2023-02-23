"""Functions for running RDFox with necessary input files and scripts, and
collecting results.

This aims to hide the complexity of setting up RDFox, loading data, adding
rules, answering queries, behind a simple function that maps data -> answers.
"""

import subprocess
import threading
import logging
from io import StringIO
import re
from pathlib import Path

from typing import List, Union, Optional, Mapping

from packaging.version import Version, parse as parse_version
from packaging.specifiers import SpecifierSet

StrPath = Union[str, Path]

from .rdfox_endpoint import RDFoxEndpoint
from .command_runner import CommandRunner, PathOrIO

logger = logging.getLogger(__name__)


VERSION_PATTERN = re.compile(r"RDFox version: ([0-9.]+).*")

ERROR_PATTERN = re.compile(r"Error: .*|"
                           r"File with name '.*' cannot be found|"
                           r"Name '.*' cannot be resolved to a file relative to either|"
                           r"Script file .* cannot be found|"
                           r"Unknown command '.*'|"
                           r"The server could not start listening")

MULTILINE_ERROR_PATTERN = re.compile(r"An error occurred while executing the command:")

ENDPOINT_PATTERN = re.compile(r"The REST endpoint was successfully started at port number/service name (\S+)")


class RDFoxVersionError(RuntimeError):
    pass


def get_rdfox_version(rdfox_executable=None):
    """Return RDFox version as a `packaging.Version` instance."""
    if rdfox_executable is None:
        rdfox_executable = "RDFox"
    command = [rdfox_executable, "sandbox", ".", "echo RDFox version: $(version)", "quit"]
    output = subprocess.check_output(command).decode()
    lines = output.splitlines()
    match = VERSION_PATTERN.match(lines[-1])
    if match:
        return parse_version(match.group(1))
    else:
        raise ValueError("Unknown output from RDFox")


def check_rdfox_version(specifier, rdfox_executable=None):
    """Raise `RDFoxVersionError` if RDFox version out of range."""

    spec = SpecifierSet(specifier)
    version = get_rdfox_version(rdfox_executable)
    if not version in spec:
        raise RDFoxVersionError("Bad RDFox version: {} does not match '{}'".format(version, spec))


class RDFoxRunner:
    """Context manager to run RDFox in a temporary directory.

    :param input_files: mapping of files {target path: source file} to set up in
        temporary working directory.
    :param script: RDFox commands to run, either as a list of strings or a
        single string.
    :param namespaces: dict of RDFlib namespaces to bind
    :param wait: whether to wait for RDFox to start the endpoint or exit when
        starting.  If None, look for the presence of an "endpoint start" command
        in `script` and wait for the endpoint if found, wait for exit otherwise.
    :param working_dir: Path to setup command in, defaults to a temporary
        directory
    :param rdfox_executable: Path RDFox executable (default "RDFox")
    :param endpoint: RDFoxEndpoint instance to use (default None, meaning use the
        built in class). This can be used to customise the endpoint interface.

    When used as a context manager, the `RDFoxRunner` instance returns
    `endpoint` for running queries etc. For more control a custom
    `RDFoxEndpoint` can be passed in. When the RDFox endpoint is started, the
    `connect()` method on the endpoint will be called with the connection
    string. The endpoint is available at the attribute `endpoint`.

    """

    def __init__(
            self,
            input_files: Mapping[str, PathOrIO],
            script: Union[List[str], str],
            namespaces: Optional[Mapping] = None,
            wait: Optional[str] = None,
            working_dir: Optional[StrPath] = None,
            rdfox_executable: Optional[StrPath] = None,
            endpoint: Optional[RDFoxEndpoint] = None,
    ):

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
                wait = "endpoint"
            else:
                wait = "exit"
        elif wait not in ("endpoint", "exit", "nothing"):
            raise ValueError("wait must be 'endpoint' or 'exit' or 'nothing'")
        self.wait = wait

        if endpoint is None:
            # Could remove namespaces in future and require a custom endpoint
            # to be passed in if namespaces need to be configured?
            endpoint = RDFoxEndpoint(namespaces)
        self.endpoint = endpoint

        # Generate the master script
        self.input_files = {
            **input_files,
            MASTER_KEY: StringIO(script),
        }
        self.command = [rdfox_executable, "sandbox", ".", f"exec {MASTER_KEY}"]
        self.working_dir = working_dir

        # Accumulate multi-line error messages
        self._multiline_error = False
        self._critical_error = False
        self._critical_error_message = ""

        # Store errors
        self.errors = []
        self.stopped_on_error = False

    def _check_for_errors(self, line):

        # Check mode: if a multi-line error message has already started, accumulate it
        if self._multiline_error:
            if line.startswith(" "):
                if self._multiline_error is True:
                    self._multiline_error = []
                self._multiline_error.append(line.strip())
                logger.error("RDFox error: %s", line.strip())
                # Treat out-of-memory as a critical error?
                if line.strip() == "The RDFox instance has run out of memory.":
                    # XXX make this less messy
                    self._critical_error_message = line.strip()
                    self._critical_error = True
                return
            else:
                # Error finished
                if isinstance(self._multiline_error, list):
                    msg = "\n".join(self._multiline_error)
                    if msg:
                        self.errors.append(msg)
                self._multiline_error = False

        elif self._critical_error and not self._critical_error_message:
            # because this is running in a different thread, don't raise here
            self._critical_error_message = line
            return

        match = ENDPOINT_PATTERN.match(line)
        if match:
            port = match.group(1)
            logger.info("RDFox started on port %s", port)
            self.endpoint.connect("http://localhost:%s" % port)
            if self._endpoint_ready is not None:
                logger.debug("Signalling that endpoint is ready...")
                self._endpoint_ready.set()

        elif ERROR_PATTERN.match(line):
            logger.error("RDFox error: %s" % line)
            self.errors.append(line)

        elif MULTILINE_ERROR_PATTERN.match(line):
            # The error is more than one line -- start accumulator mode
            logger.debug("Starting multiline error message")
            self._multiline_error = True

        elif line == "A critical error occurred while running RDFox:":
            logger.debug("Starting critical error message")
            self._critical_error = True

        elif line.startswith("Stopping shell evaluation due to 'on-error' policy"):
            logger.error("RDFox error: %s", line)
            self.stopped_on_error = True
            self.send_quit()
            if self._endpoint_ready is not None:
                self._endpoint_ready.set()

    def start(self):
        """Start RDFox.

        :param wait_secs: how many seconds to wait for RDFox to start.
        """
        wait_for_exit = (self.wait == "exit")
        wait_for_endpoint = (self.wait == "endpoint")

        logger.debug("Starting to run RDFox (wait_for_exit=%s, wait_for_endpoint=%s)",
                     wait_for_exit, wait_for_endpoint)
        self._runner = CommandRunner(
            self.input_files,
            self.command,
            working_dir=self.working_dir,
            output_callback=self._check_for_errors,
        )

        if wait_for_endpoint:
            self._endpoint_ready = threading.Event()
            self._runner.start()
            logger.debug("CommandRunner started, waiting for endpoint...")
            self._endpoint_ready.wait()
            self.raise_for_errors()
            logger.debug("...endpoint ready!")
        else:
            self._endpoint_ready = None
            self._runner.start()

            if wait_for_exit:
                logger.debug("CommandRunner started, waiting for exit...")
                self._runner.wait()
                self.raise_for_errors()
            else:
                logger.debug("CommandRunner started.")

    def send_quit(self):
        """Send "quit" command to RDFox."""
        logger.debug("Sending 'quit' command to RDFox")

        if not (self._runner and self._runner._process and self._runner._process.stdin):
            return

        try:
            self._runner._process.stdin.write(b"quit\n")
            self._runner._process.stdin.flush()
        except (OSError, BrokenPipeError, ValueError):
            # On Windows it's an OSError, see https://bugs.python.org/issue35754
            pass

    def stop(self):
        """Stop RDFox."""
        logger.debug("Stopping RDFox")

        # Try to exit gracefully first
        self.send_quit()

        self._runner.stop()
        self.raise_for_errors()

    def raise_for_errors(self):
        """Raise an exception if RDFox has reported an error.

        Currently this only reports "critical" errors.

        """
        logger.debug("raise_for_errors: %s, %s", self._critical_error, self._critical_error_message)
        if self._critical_error:
            raise RuntimeError(f"Critical RDFox error: {self._critical_error_message}")

    def __enter__(self):
        self.start()
        return self.endpoint

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
        kwargs["wait"] = "exit"

    result = {}
    runner = RDFoxRunner(input_files, script, **kwargs)
    with runner:
        for key, filename in output_files.items():
            result[key] = runner.files(filename).read_text()
    return result
