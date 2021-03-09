"""This module defines a function to run a command in a temporary directory,
with specified input files present, and captures the contents of specified
output files.

This is the simplest building block used as the base for probs_runner.

"""


import logging
import subprocess
import shutil
from pathlib import Path
from tempfile import mkdtemp

from typing import Any, Callable, Dict, List, Union, Optional, TextIO, Mapping

StrPath = Union[str, Path]
PathOrIO = Union[StrPath, TextIO]

logger = logging.getLogger(__name__)


class WorkingDirectory:
    """Like TemporaryDirectory, but in the current directory and not deleted."""

    def __init__(self, name=None):
        if name is None:
            self.name = Path(mkdtemp())
            self.keep = False
        else:
            self.keep = True
            self.name = Path(name)
            if self.name.exists() and any(self.name.iterdir()):
                logger.warning(f"Existing working directory not empty {self.name}")

        # while self.name.exists():
        #     self.name = Path(str(name) + "_" + time.strftime("%Y%m%d-%H%M"))

        self.name.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created temporary working directory {self.name}")

    def __enter__(self):
        """For use as context manager."""
        return self.name

    def __exit__(self, exc, value, tb):
        """Tidy up after context manager"""
        if not self.keep:
            self.cleanup()

    def cleanup(self):
        shutil.rmtree(self.name, ignore_errors=True)
        logger.debug(f"Removed temporary working directory {self.name}")


def run_in_dir(
    input_files: Optional[Mapping[str, PathOrIO]] = None,
    output_files: Optional[Mapping[Any, StrPath]] = None,
    command: Optional[Union[List, str]] = None,
    shell: bool = False,
    working_dir: Optional[StrPath] = None,
    output_callback: Optional[Callable] = None,
) -> Dict[Any, str]:
    """Prepare temporary directory with input_files and run command.

    :param input_files: list of (target path, source path) pairs
    :param output_files: dict of {label: target path} to collect
    :param command: command to run, as passed to subprocess.Popen
    :param shell: whether to run command within shell
    :param working_dir: Path to setup command in, defaults to a temporary directory
    :param output_callback: Callback on output from command
    :return: Dict of {label: result}
    """

    if input_files is None:
        input_files = {}
    if output_files is None:
        output_files = {}

    with WorkingDirectory(working_dir) as tempdir:
        logger.info("Setting up to run command in %s", tempdir)
        for target, source in input_files.items():
            copy_files(source, tempdir / target)
        if command:
            run_subprocess(command, cwd=tempdir, output_callback=output_callback, shell=shell)
        result = get_file_contents(tempdir, output_files)

    return result


def copy_files(src: PathOrIO, dst: Path):
    if isinstance(src, (Path, str)):
        src = Path(src)
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            logger.debug("Copying directory %s to %s", src, dst)
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            logger.debug("Copying file %s to %s", src, dst)
            shutil.copy(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Writing data %s", dst)
        with open(dst, "wt") as f:
            f.write(src.read())


def get_file_contents(root_path: Path, output_files: Mapping[Any, StrPath]):
    """Read the contents of output_files.

    :param root_path: Root path that output_files are relative to
    :param output_files: Dict of {label: target path} to collect
    :return: Dict of {label: result}
    """
    result = {}
    for label, rel_path in output_files.items():
        with open(root_path / rel_path, "rt") as f:
            result[label] = f.read()
    return result


def run_subprocess(cmd, cwd=None, shell=False, output_callback=None):
    logger.info("Running command '%s'", cmd)

    with subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line buffered
        shell=shell,
    ) as process:
        for line in iter(process.stdout.readline, ""):
            logger.debug("cmd> %s", line.rstrip())
            if output_callback:
                output_callback(line.rstrip())

    if process.returncode != 0:
        logger.error("Error running command: %d", process.returncode)
        raise subprocess.CalledProcessError(process.returncode, cmd=cmd)
