"""
Configure environments to test rdfox runner across multiple RDFox versions.
"""

import platform
import nox


PLATFORM_NAMES = {
    "Darwin": "macOS",
    "Linux": "linux",
    "Windows": "win64",
}

def download_rdfox(session, version):
    if platform.system() in PLATFORM_NAMES:
        pfm = PLATFORM_NAMES[platform.system()]
    else:
        raise RuntimeError("Unsupported OS platform")
    machine = platform.machine()
    name = f"RDFox-{pfm}-{machine}-{version}"
    session.log("Fetching s: %RDFox", name)


@nox.session
@nox.parametrize('rdfox', ["5.6", "6.2"], ids=["rdfox62", "rdfox56"])
def tests(session, rdfox):
    session.install("pytest~=5.2")
    session.install(f"rdfox=={rdfox}")
    session.install("-e", ".")
    session.run("pytest", "tests", "--log-level=DEBUG", *session.posargs)
