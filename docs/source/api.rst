API Reference
=============

RDFox endpoint
--------------

The :class:`rdfox_runner.RDFoxEndpoint` class helps to interface with a running RDFox endpoint.

.. autoclass:: rdfox_runner.RDFoxEndpoint
    :members:

RDFox runner
------------

The :class:`rdfox_runner.RDFoxRunner` class handles starting and stopping an RDFox instance with a specified set of input files and a script to run. It derives from :class:`rdfox_runner.RDFoxEndpoint` so the same query methods can be used once it is running.

.. autoclass:: rdfox_runner.RDFoxRunner
    :show-inheritance:
    :members:


Generic command runner
----------------------

The :class:`rdfox_runner.CommandRunner` class is the building block for rdfox_runner, which handles setting up a temporary working directory and running a given command within it.

For example::

    from io import StringIO
    import time

    input_files = {
        "a.txt": StringIO("hello world"),
    }

    # The -u is important for unbuffered output
    command = ["python", "-u", "-m", "http.server", "8008"]

    with CommandRunner(input_files, command):
        time.sleep(0.1)
        response = requests.get("http://localhost:8008/a.txt")

    assert response.text == "hello world"

.. autoclass:: rdfox_runner.CommandRunner
    :members:


    The values in `input_files` can be:

    - a :class:`pathlib.Path` or string -- interpreted as a path to a file to
        copy
    - a file-like object -- read to provide the content for the temporary file.
        This can be a :class:`io.StringIO` object if you would like to provide a
        constant value
