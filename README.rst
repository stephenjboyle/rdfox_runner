==============
 rdfox_runner
==============

Set up and run `RDFox`_ scripts in a temporary directory.

Requires RDFox version 5.0 or greater for the `RDFoxEndpoint.add_triples` method.

`rdfox_runner` is tested against the latest version of RDFox (currently 5.6).


Description
===========

This Python package provides functions for running RDFox in a functional way: mapping from input facts/rules to output facts/answers. It hides the process of setting up RDFox scripts and input files in a temporary directory, running RDFox, and extracting the results. It can also be used to interact with an externally-running RDFox REST endpoint.

See the `documentation`_ for more details.


Installation
============

Install rdfox_runner using pip:

.. code-block:: shell

    pip install rdfox_runner


Contributing 🎁
===============

Contributions are welcome: share examples of work done using it, make suggestions for improving the documentation, and examples of things that are more difficult than they should be or don't work -- as well as of course making actual fixes to code and documentation.

See `DEVELOPING.rst <DEVELOPING.rst>`_ for more information.

License
=======

rdfox_runner is licensed with the `MIT license <LICENSE>`_.

`RDFox`_ is created by Oxford Semantic Technologies, who are not responsible for this project.

.. _RDFox: https://www.oxfordsemantic.tech/product
.. _documentation: https://rdfox-runner.readthedocs.io/en/latest/
