# Get version; fallback import for Python <3.8
try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata

try:
    __version__ = importlib_metadata.version("rdfox_runner")
except importlib_metadata.PackageNotFoundError:
    # Not installed
    __version__ = "dev"

from .command_runner import CommandRunner
from .run_rdfox import RDFoxEndpoint, RDFoxRunner, RDFoxVersionError, get_rdfox_version, check_rdfox_version

__all__ = [
    "RDFoxEndpoint",
    "RDFoxRunner",
    "CommandRunner",
    "RDFoxVersionError",
    "get_rdfox_version",
    "check_rdfox_version",
]
