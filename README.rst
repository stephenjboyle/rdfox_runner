============
rdfox_runner
============


Set up and run RDFox scripts in a temporary directory.


Description
===========

This Python package provides functions for running RDFox in a functional way: mapping from input facts/rules to output facts/answers. It hides the process of setting up RDFox scripts and input files in a temporary directory, running RDFox, and extracting the results.

There are two "layers":
- `run_in_dir` takes a set of input files, sets them up in a temporary working directory, runs a command and returns the contents of some output files. This is generic (nothing specific to RDFox).
- `run_rdfox` is similar, but its input is an RDFox script to run with the input files.
