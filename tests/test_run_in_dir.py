# -*- coding: utf-8 -*-

import subprocess
import pytest
from unittest.mock import Mock
from io import StringIO

from rdfox_runner import run_in_dir


@pytest.fixture
def test_files(tmp_path):
    # Set up test files
    (tmp_path / "source_subdir").mkdir()
    with open(tmp_path / "source_subdir/a.txt", "wt") as f:
        f.write("a")
    with open(tmp_path / "source_subdir/b.txt", "wt") as f:
        f.write("b")
    return tmp_path


def test_cat(test_files):
    input_files = {
        "a.txt": test_files / "source_subdir/a.txt",
        "target_subdir/b.txt": test_files / "source_subdir/b.txt",
    }
    output_files = {
        "label": "result.txt",
    }
    command = "cat a.txt target_subdir/b.txt > result.txt"
    result = run_in_dir(input_files, output_files, command, shell=True)

    assert result == {"label": "ab"}


def test_mv(test_files):
    input_files = {
        "a.txt": test_files / "source_subdir/a.txt",
        "target_subdir/b.txt": test_files / "source_subdir/b.txt",
    }
    output_files = {
        "file_a": "result_a.txt",
        "file_b": "result_b.txt",
    }
    command = "mv a.txt result_a.txt && mv target_subdir/b.txt result_b.txt"
    result = run_in_dir(input_files, output_files, command, shell=True)

    assert result == {
        "file_a": "a",
        "file_b": "b",
    }


def test_file_object_as_input():
    input_files = {
        "a.txt": StringIO("hello"),
        "subdir/b.txt": StringIO("world"),
    }
    output_files = {
        "a": "a.txt",
        "b": "subdir/b.txt",
    }
    result = run_in_dir(input_files, output_files)

    assert result == {
        "a": "hello",
        "b": "world",
    }


def test_mv_missing_file(test_files):
    input_files = {
        "a.txt": test_files / "source_subdir/a.txt",
    }
    output_files = {
        "label": "result.txt",
    }
    command = ["mv", "target_subdir/b.txt", "result.txt"]

    with pytest.raises(subprocess.CalledProcessError):
        run_in_dir(input_files, output_files, command, shell=False)


def test_output_callback():
    input_files = {}
    output_files = {}
    command = ["echo", "this is an error"]
    callback = Mock()

    run_in_dir(
        input_files, output_files, command, output_callback=callback, shell=False
    )

    assert callback.call_args == (("this is an error",),)
