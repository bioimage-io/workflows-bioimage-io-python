import os

DEFAULT_SERVER_URL = "http://localhost:9000"
SERVER_URL_VAR_NAME = "BIOIMAGEIO_SERVER_URL"
SERVER_URL = os.getenv(SERVER_URL_VAR_NAME, DEFAULT_SERVER_URL)
AUTOSTART_SERVER_VAR_NAME = "BIOIMAGEIO_AUTOSTART_SERVER"
AUTOSTART_SERVER = os.getenv(AUTOSTART_SERVER_VAR_NAME, "true").lower() in ("true", "1")
AUTOSTART_ENV_SERVICES_VAR_NAME = "BIOIMAGEIO_AUTOSTART_ENV_SERVICES"
AUTOSTART_ENV_SERVICES = os.getenv(AUTOSTART_SERVER_VAR_NAME, "true").lower() in ("true", "1")
AUTOINSTALL_SUBMODULE_ENVS = os.getenv("BIOIMAGEIO_AUTOINSTALL_SUBMODULE_ENVS", "true").lower() in ("true", "1")
START_SUBMODULE_SERVICE_NAME = "bioimageio-wf-start-service"


def get_env_specific_server_url_var_name(env_name) -> str:
    return f"BIOIMAGEIO_SERVER_{env_name.upper()}_URL"


def get_server_url(env_name: str) -> str:
    return os.getenv(get_env_specific_server_url_var_name(env_name), SERVER_URL)


def get_env_service_name(env_name: str) -> str:
    return f"bioimageio-wf-service-{env_name}"


def get_conda_env_name(env_name: str) -> str:
    return f"bioimageio_wf_env_{env_name}"


SERVER_CONDA_ENV = os.getenv("BIOIMAGE_SERVER_CONDA_ENV", get_conda_env_name("default"))
