import json
import pathlib

import packaging.version

__version__ = json.loads((pathlib.Path(__file__).parent / "VERSION").read_text())["version"]


Version = packaging.version.Version

CURRENT_VERSION = Version(__version__)
