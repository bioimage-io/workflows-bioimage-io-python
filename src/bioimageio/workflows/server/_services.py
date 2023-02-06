import asyncio
import contextlib
import logging
from importlib import import_module
from inspect import getmembers, isfunction

from bioimageio.workflows.server._utils import ensure_conda_env_exists, get_server
from bioimageio.workflows.server.env_vars import (
    START_SUBMODULE_SERVICE_NAME,
    get_conda_env_name,
    get_env_service_name,
)

logger = logging.getLogger(__name__)


async def register_submodule_service_launcher():
    server = await get_server()

    long_service_name = "BioImageIO Submodule Service Launcher"
    service_name = START_SUBMODULE_SERVICE_NAME
    launcher = SubmoduleServiceLauncher()
    service_config = dict(
        name=long_service_name,
        id=service_name,
        config={
            "visibility": "public",
            "run_in_executor": True,  # This will make sure all the sync functions run in a separate thread
        },
        start_submodule_service=launcher.start_submodule_service,
        health_check=launcher.health_check
    )

    await server.register_service(service_config)

    logger.info(f"{long_service_name} (id: {service_name}) registered at workspace: {server.config.workspace}")


class SubmoduleServiceLauncher:
    def __init__(self):
        self.procs = []

    async def start_submodule_service(self, env_name: str):
        conda_env_name = get_conda_env_name(env_name)
        ensure_conda_env_exists(conda_env_name)
        cmd = (
            f"conda run -n {conda_env_name} "
            f"python -m bioimageio.workflows.server start-submodule-service {env_name}"
        )
        print(f"starting submodule service: {cmd}")
        self.procs.append(
            asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        )

    @staticmethod
    async def is_running(proc):
        """check on asyncio subprocess; from https://stackoverflow.com/a/65880634/17492107"""
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(proc.wait(), 1e-6)

        return proc.returncode is None

    async def health_check(self):
        return f"procs: {[]}"


async def register_submodule_service(env_name: str):
    """Start a service per environment name to a hypha server which provides the functionality of that
    environment specific workflow submodule."""

    server = await get_server(env_name)

    env = import_module(f"bioimageio.workflows.envs.{env_name}.local")  # import local env
    long_service_name = f"BioImageIO {' '.join(n.capitalize() for n in env_name.split('_'))} Submodule Service"
    service_name = get_env_service_name(env_name)
    service_config = dict(
        name=long_service_name,
        id=service_name,
        config={
            "visibility": "public",
            "run_in_executor": True,  # This will make sure all the sync functions run in a separate thread
        },
    )

    for func_name, func in getmembers(env, isfunction):
        assert func_name not in service_config
        print("registered", func_name)
        service_config[func_name] = func

    await server.register_service(service_config)

    logger.info(f"{long_service_name} (id: {service_name}) registered at workspace: {server.config.workspace}")
