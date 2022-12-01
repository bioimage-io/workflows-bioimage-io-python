import sys
from pathlib import Path

from bioimageio.workflows.server import RemoteSubmodule

remote_module = RemoteSubmodule(Path(__file__).parent.stem)
__all__ = remote_module.__all__
sys.modules[__name__] = remote_module  # noqa
