"""Functions for running RDFox with necessary input files and scripts, and
collecting results.

This aims to hide the complexity of setting up RDFox, loading data, adding
rules, answering queries, behind a simple function that maps data -> answers.
"""


import logging
from io import StringIO
import re
from pathlib import Path

from typing import Any, Dict, List, Union, Optional, Mapping

StrPath = Union[str, Path]

from .run_in_dir import run_in_dir, PathOrIO

logger = logging.getLogger(__name__)


ERROR_PATTERN = re.compile(r"Error: .*|"
                           r"File with name '.*' cannot be found|"
                           r"An error occurred while executing the command:")


def run_rdfox(
    input_files: Mapping[str, PathOrIO],
    output_files: Mapping[Any, StrPath],
    script: Union[List, str],
    working_dir: Optional[StrPath] = None,
    rdfox_executable: Optional[StrPath] = None,
) -> Dict[Any, str]:
    """Setup RDFox with input_files, run script, return contents of output_files.

    :param input_files: list of (target path, source path) pairs
    :param output_files: dict of {label: target path} to collect
    :param script: RDFox commands to run
    :param working_dir: Path to setup command in, defaults to a temporary directory
    :return: Dict of {label: result}
    """

    MASTER_KEY = "__master.rdfox"
    if MASTER_KEY in input_files:
        raise ValueError(f'Cannot have an input file named "{MASTER_KEY}"')

    if not isinstance(script, str):
        script = "\n".join(script)

    if rdfox_executable is None:
        rdfox_executable = "RDFox"

    # Generate the master script
    input_files = {
        **input_files,
        MASTER_KEY: StringIO(script),
    }

    command = [rdfox_executable, "sandbox", ".", f"exec {MASTER_KEY}"]

    def check_for_errors(line):
        if ERROR_PATTERN.match(line):
            logger.error("RDFox error: %s" % line)
            # TODO often the error is more than one line -- should keep printing
            # while the next lines are indented.

    logger.debug("Running RDFox")
    result = run_in_dir(input_files, output_files, command, working_dir=working_dir, output_callback=check_for_errors)

    return result
