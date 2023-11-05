import pytest
from packaging.version import Version
from rdfox_runner.run_rdfox import get_rdfox_version

# Define as a fixture so result is cached
@pytest.fixture(scope="session")
def rdfox_version():
    return get_rdfox_version()


@pytest.fixture(scope="session")
def setup_script(rdfox_version):
    setup = [
        # Stop execution on any error
        "set on-error stop",
    ]
    if rdfox_version < Version("6.0"):
        setup += ["dstore create default type par-complex-nn"]
    else:
        setup += ["dstore create default type parallel-nn"]
    return setup
