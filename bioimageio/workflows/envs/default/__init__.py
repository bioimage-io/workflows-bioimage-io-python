import os

BIOIMAGEIO_USE_REMOTE_DEFAULT_ENV = os.getenv("BIOIMAGEIO_USE_REMOTE_DEFAULT_ENV")
if BIOIMAGEIO_USE_REMOTE_DEFAULT_ENV is None or BIOIMAGEIO_USE_REMOTE_DEFAULT_ENV.lower() in (
    "false",
    "0",
):
    from .local import *
elif BIOIMAGEIO_USE_REMOTE_DEFAULT_ENV.lower() in ("true", "1"):
    from .remote import *
else:
    raise ValueError(
        "Failed to interpret environment variable 'BIOIMAGEIO_USE_REMOTE_DEFAULT_ENV'. "
        f"Expected one of: true, 1, false, 0, but got {BIOIMAGEIO_USE_REMOTE_DEFAULT_ENV}."
    )
