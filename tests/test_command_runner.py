# -*- coding: utf-8 -*-

import os
import time
import subprocess
import pytest
from unittest.mock import Mock
from io import StringIO
import requests
import platform

from rdfox_runner.command_runner import CommandRunner


IS_CMD_EXE = os.environ.get("COMSPEC", "").lower().endswith("cmd.exe")
IS_POWERSHELL = os.environ.get("COMSPEC", "").lower().endswith("powershell.exe")

MOVE_COMMAND = "move" if IS_CMD_EXE else "mv"
AND_AND = "&&" if not IS_POWERSHELL else ";"


@pytest.fixture
def test_files(tmp_path):
    # Set up test files
    (tmp_path / "source_subdir").mkdir()
    with open(tmp_path / "source_subdir/a.txt", "wt") as f:
        f.write("a")
    with open(tmp_path / "source_subdir/b.txt", "wt") as f:
        f.write("b")
    return tmp_path


def test_http_server(test_files):
    """Test running code while the command is still running."""
    input_files = {
        "a.txt": test_files / "source_subdir/a.txt",
        "target_subdir/b.txt": test_files / "source_subdir/b.txt",
    }

    # The -u is important for unbuffered output
    command = ["python", "-u", "-m", "http.server", "8008"]

    with CommandRunner(input_files, command, shell=False):
        time.sleep(1)
        response = requests.get("http://localhost:8008/a.txt")

    assert response.text == "a"


def test_wait_before_enter_waits_for_command_to_complete(test_files):
    input_files = {
        "a.txt": test_files / "source_subdir/a.txt",
        "target_subdir/b.txt": test_files / "source_subdir/b.txt",
    }
    if IS_CMD_EXE:
        command = "ping -n 1 127.0.0.1 && move a.txt result.txt"
    else:
        command = f"sleep 0.51 {AND_AND} mv a.txt result.txt"
    
    with CommandRunner(input_files, command, shell=True, wait_before_enter=True) as ctx:
        result = ctx.files("result.txt").read_text()

    assert result == "a"


def test_lack_of_wait_before_enter_leads_to_failure(test_files):
    input_files = {
        "a.txt": test_files / "source_subdir/a.txt",
        "target_subdir/b.txt": test_files / "source_subdir/b.txt",
    }
    if IS_CMD_EXE:
        command = "ping -n 1 127.0.0.1 && move a.txt result.txt"
    else:
        # On powershell seems to round to integer so 0.5 is too little...
        command = f"sleep 0.51 {AND_AND} mv a.txt result.txt"
    
    with pytest.raises(FileNotFoundError):
        with CommandRunner(input_files, command, shell=True) as ctx:
            ctx.files("result.txt").read_text()


def test_file_object_as_input():
    input_files = {
        "a.txt": StringIO("hello"),
        "subdir/b.txt": StringIO("world"),
    }

    with CommandRunner(input_files) as ctx:
        result_a = ctx.files("a.txt").read_text()
        result_b = ctx.files("subdir/b.txt").read_text()

    assert result_a == "hello"
    assert result_b == "world"


def test_no_errors_reported_for_successful_command(caplog):
    # As long as the command exits cleanly, should be no error
    command = ["python", "--version"]
    with CommandRunner({}, command, wait_before_exit=True) as ctx:
        pass

    for record in caplog.records:
        assert record.levelname not in ["CRITICAL", "ERROR"]


def test_mv_missing_file_no_wait():
    if IS_CMD_EXE:
        command = "ping -n 5 127.0.0.1"
    else:
        command = "sleep 5"

    with CommandRunner({}, command, shell=True) as ctx:
        # The subprocess has not finished yet
        assert ctx.returncode is None

    # Outside of the block, the subprocess should have been terminated; but the
    # numeric return code for this is different on different platforms
    if platform.system() == "Windows":
        expected_return_code = 1
    else:
        expected_return_code = -15
    assert ctx.returncode == expected_return_code


def test_mv_missing_file_wait_before_enter():
    command = [MOVE_COMMAND, "target_subdir/b.txt", "result.txt"]

    # Shell needed on Windows cmd.exe
    with CommandRunner({}, command, shell=True, wait_before_enter=True) as ctx:
        assert ctx.returncode and ctx.returncode >= 1


def test_mv_missing_file_wait_before_exit():
    command = [MOVE_COMMAND, "target_subdir/b.txt", "result.txt"]

    # Shell needed on Windows cmd.exe
    with CommandRunner({}, command, shell=True, wait_before_exit=True) as ctx:
        # The subprocess has not finished yet
        assert ctx.returncode is None

    # Outside of the block, the subprocess should have finished
    assert ctx.returncode and ctx.returncode >= 1


def test_output_callback():
    input_files = {}
    command = "echo error"
    callback = Mock()

    # Shell needed on Windows cmd.exe
    with CommandRunner(input_files, command, shell=True, output_callback=callback, wait_before_exit=True):
        pass

    assert callback.call_args == (("error",),)


class TestWorkingDir:
    def test_working_dir_present_in_context_then_removed(self):
        # Shell needed on Windows cmd.exe
        with CommandRunner(command=["echo", "hello"], shell=True) as ctx:
            assert ctx.working_dir is not None
            assert ctx.working_dir.exists()
            tmp = ctx.working_dir

        assert ctx.working_dir is None
        assert not tmp.exists()

    def test_explicit_working_dir_is_not_removed(self, tmp_path):
        # Shell needed on Windows cmd.exe
        with CommandRunner(command=["echo", "hello"], shell=True, working_dir=tmp_path) as ctx:
            assert ctx.working_dir == tmp_path

        assert ctx.working_dir == tmp_path
        assert tmp_path.exists()
