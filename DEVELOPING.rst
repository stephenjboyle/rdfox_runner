=========================
 Developing rdfox_runner
=========================

Documentation
=============

Documentation is written using Sphinx. It is hosted on ReadTheDocs. Changes should be automatically rebuilt and reflected there.

Releases
========

To release a new version of rdfox_runner:

- Ensure tests are passing, documentation is up to date.

- Bump the version number as appropriate, based on the type of changes made since the last release::

    poetry version (patch | minor | major)

- Commit the new version and tag a release like "v0.1.2"

- Build the package::

    poetry build

- Publish the package to PyPI::

    poetry publish

Tests
=====

To run the tests against multiple versions of RDFox, we use `nox`_. You can install it globally (as the nox project recommends), or it will be installed within the poetry Python environment and can be used with `poetry run nox ...` or within `poetry shell`.

Run all the tests using nox::

    nox

To quickly re-run when no dependencies have changed (only edits to existing files) use the `-R` option to reuse the virtual environments::

    nox -R

Pass additional options to pytest after `--`, e.g.::

    nox -R -- --log-cli-level=DEBUG -x

.. _nox: https://nox.thea.codes/
