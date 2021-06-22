"""This module defines a function to run a command in a temporary directory,
with specified input files present, and captures the contents of specified
output files.

This is the simplest building block used as the base for rdfox_runner.

"""


import os
import logging
import subprocess
import shutil
from pathlib import Path
from tempfile import mkdtemp
import threading

from typing import Any, Callable, List, Union, Optional, TextIO, Mapping

StrPath = Union[str, Path]
PathOrIO = Union[StrPath, TextIO]

logger = logging.getLogger(__name__)


class CommandRunner:
    """Run a command in a temporary directory.

    This can be used as a context manager, ensuring the temporary directory is
    cleaned up and the subprocess is stopped when finished with.

    :param input_files: mapping with keys being the target path and value the
        source path.
    :param command: command to run, as passed to :class:`subprocess.Popen`
    :param shell: whether to run command within shell
    :param wait_before_enter: whether to wait for command to complete before
        continuing with context manager body.
    :param wait_before_exit: whether to wait for command to complete by itself
        before terminating it, when leaving context manager body.
    :param timeout: timeout if `wait` is true.
    :param working_dir: Path to setup command in, defaults to a temporary
        directory
    :param output_callback: Callback on output from command.
    """

    def __init__(
            self,
            input_files: Optional[Mapping[str, PathOrIO]] = None,
            command: Optional[Union[List, str]] = None,
            shell: bool = False,
            wait_before_enter: bool = False,
            wait_before_exit: bool = False,
            timeout: Optional[float] = None,
            working_dir: Optional[StrPath] = None,
            output_callback: Optional[Callable] = None,
        ):

        if working_dir is not None:
            working_dir = Path(working_dir)
            if working_dir.exists() and any(working_dir.iterdir()):
                logger.warning(f"Existing working directory not empty: {working_dir}")

        self.input_files = input_files or {}
        self.command = command
        self.shell = shell
        self.wait_before_enter = wait_before_enter
        self.wait_before_exit = wait_before_exit
        self.timeout = timeout
        self.working_dir = working_dir
        self.output_callback = output_callback

        self._process = None
        self._cleanup_working_dir = (working_dir is None)

        if os.environ.get("RDFOX_RUNNER_KEEP_WORKING_DIR", ""):
            self._cleanup_working_dir = False

    def start(self):
        """Setup files and start the command running.

        This is a convenience method to run :meth:`setup_files` and
        :meth:`start_subprocess` together, as needed.
        """
        self.setup_files()
        if self.command:
            self.start_subprocess()

    def stop(self):
        """Stop the command and clean up files.

        This is a convenience method to run :meth:`stop_subprocess` and
        :meth:`cleanup_files` together, as needed.

        :raises subprocess.CalledProcessError: if the subprocess returns an
            error exit code.
        """
        if self.command:
            self.stop_subprocess()
        if self._cleanup_working_dir:
            self.cleanup_files()

    def setup_files(self):
        """Setup the files ready to run the command.

        If :attr:`working_dir` has been specified, it is created if it does not
        exist.  Otherwise, a new temporary directory is created.

        The files listed in :attr:`input_files` are copied into the working
        directory.
        """
        if self.working_dir is None:
            self.working_dir = Path(mkdtemp())
            logger.debug("Created temporary working directory %s", self.working_dir)
        elif not self.working_dir.exists():
            self.working_dir.mkdir(parents=True)
            logger.debug("Created temporary working directory %s", self.working_dir)

        logger.info("Setting up to run command in %s", self.working_dir)

        for target, source in self.input_files.items():
            copy_files(source, self.working_dir / target)

    def start_subprocess(self):
        """Start the subprocess running.

        If :attr:`wait` is true, wait for up to :attr:`timeout` seconds before
        continuing.
        """
        if self.command is None:
            return

        logger.info("Running command '%s'", self.command)

        self._process = subprocess.Popen(
            self.command,
            cwd=self.working_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # text=True,
            # bufsize=1,  # line buffered
            shell=self.shell,
        )

        self._output_thread = threading.Thread(target=output_reader,
                                               args=(self._process, self.output_callback))
        self._output_thread.daemon = True
        self._output_thread.start()

        logger.debug("finished starting")

    def wait(self):
        """Wait for subprocess to exit.

        Waits up to :attr:`timeout` seconds.
        """
        if self.timeout is not None:
            logger.debug("waiting %.1f s for subprocess to finish...", self.timeout)
        else:
            logger.debug("waiting for ever for subprocess to finish...")
        try:
            self._process.wait(timeout=self.timeout)
            logger.info('Subprocess exited with returncode = %s', self._process.returncode)
        except subprocess.TimeoutExpired:
            logger.error('Subprocess did not terminate in time when waiting, continuing')

    def stop_subprocess(self):
        """Stop the subprocess. """
        if self.command is None:
            return

        if not self._process:
            logger.warning("trying to stop process that wasn't started")
            return

        logger.debug("trying to terminate processs...")
        try:
            self._process.stdin.close()
        except (OSError, BrokenPipeError):
            # On Windows it's an OSError, see https://bugs.python.org/issue35754
            pass
        self._process.terminate()
        logger.debug("...terminate returned.")
        try:
            logger.debug("waiting for process to exit...")
            self._process.wait(timeout=5)
            logger.info('Subprocess exited with returncode = %s', self._process.returncode)
        except subprocess.TimeoutExpired:
            logger.error('Subprocess did not terminate in time')
            self._process.kill()

        self._output_thread.join()

        self._process.poll()  # update returncode
        if self._process.returncode > 0:
            logger.error("Error running command: %d", self._process.returncode)
            # raise subprocess.CalledProcessError(self._process.returncode, cmd=self.command)
        elif self._process.returncode < 0:
            logger.warning("Process was killed: returncode=%d", self._process.returncode)

    @property
    def returncode(self):
        if self._process:
            return self._process.returncode
        return None

    def cleanup_files(self):
        """Cleanup temporary working directory, if needed.

        The directory is only removed if it was newly created, not if it was
        passed in as :attr:`working_dir`.
        """
        if self.working_dir is not None:
            if not self._cleanup_working_dir:
                logger.warning("trying to cleanup working directory that wasn't created")
                return

            shutil.rmtree(self.working_dir, ignore_errors=True)
            logger.debug(f"Removed temporary working directory {self.working_dir}")
            self.working_dir = None

    def __enter__(self):
        self.start()
        if self.wait_before_enter:
            self.wait()
        return self

    def __exit__(self, exc, value, tb):
        if self.wait_before_exit:
            self.wait()
        self.stop()

    def files(self, path) -> Path:
        """Return path to temporary directory.

        :param path: path relative to the working directory
        """
        return self.working_dir / path


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


def output_reader(process, output_callback):
    logger.debug("output reader started (output_callback=%s)", output_callback)
    for line in iter(process.stdout.readline, b""):
        line = line.decode("utf-8").rstrip()
        # line = line.rstrip()
        logger.debug("cmd> %s", line)
        if output_callback:
            output_callback(line)
