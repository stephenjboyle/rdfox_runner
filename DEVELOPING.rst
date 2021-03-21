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
