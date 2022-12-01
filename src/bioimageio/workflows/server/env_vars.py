import os

from bioimageio.workflows import __version__

DEFAULT_SERVER_URL = "http://localhost:9000"
SERVER_URL_VAR_NAME = "BIOIMAGEIO_SERVER_URL"
SERVER_URL = os.getenv(SERVER_URL_VAR_NAME, DEFAULT_SERVER_URL)
BIOIMAGEIO_AUTOSTART_SERVER_VAR_NAME = "BIOIMAGEIO_AUTOSTART_SERVER"
AUTOSTART_SERVER = os.getenv(BIOIMAGEIO_AUTOSTART_SERVER_VAR_NAME, "true").lower() in ("true", "1")
AUTOINSTALL_SUBMODULE_ENVS = os.getenv("BIOIMAGEIO_AUTOINSTALL_SUBMODULE_ENVS", "true").lower() in ("true", "1")


def get_env_specific_server_url_var_name(env_name) -> str:
    return f"BIOIMAGEIO_SERVER_{env_name.upper()}_URL"


def get_server_url(env_name: str) -> str:
    return os.getenv(get_env_specific_server_url_var_name(env_name), SERVER_URL)


SERVER_CONDA_ENV = os.getenv("BIOIMAGE_IO_SERVER_CONDA_ENV", "default")
# DEFAULT_ENV_DEPS = [
#     f"bioimageio.workflows=={__version__}",
#     "hypha",
#     "onnxruntime>=1.12",
#     "pytorch>=1.13",
#     "torchvision",
#     "tensorflow==2.*",
# ]


def get_conda_env_name(env_name: str) -> str:
    return f"bioimageio_wf_env_{env_name}"
