import ast
import asyncio
import atexit
import logging
import subprocess
import warnings
from functools import partial
from inspect import getmembers, isfunction
from pathlib import Path
from typing import List, Optional

from imjoy_rpc.hypha import connect_to_server

from bioimageio.workflows import envs
from bioimageio.workflows.server.env_vars import (
    AUTOINSTALL_SUBMODULE_ENVS,
    AUTOSTART_SERVER,
    SERVER_URL_VAR_NAME,
    get_conda_env_name,
    get_env_specific_server_url_var_name,
    get_server_url,
)
from bioimageio.workflows.utils import get_ast_tree

logger = logging.getLogger(__name__)


def run_submodule_services(*environment_name: str, server_url: Optional[str] = None):
    """Register one service per environment name to a hypha server which provides the functionality of that
    environment specific workflow submodule.

    To be run from a conda environment compatible with every given `environment_name`.
    """
    loop = asyncio.get_event_loop()
    for en in environment_name:
        loop.create_task(start_submodule_service(en, server_url=server_url))

    loop.run_forever()


async def start_submodule_service(env_name: str, server_url: Optional[str] = None):
    """Start a service per environment name to a hypha server which provides the functionality of that
    environment specific workflow submodule."""

    server = await connect_to_server({"server_url": server_url or get_server_url(env_name)})

    env = getattr(envs, env_name)
    service_name = f"BioImageIO {' '.join(n.capitalize() for n in env_name.split('_'))} Workflow Module"
    service_config = dict(
        name=service_name,
        id=f"bioimageio-wf-service-{env_name}",
        config={
            "visibility": "public",
            "run_in_executor": True,  # This will make sure all the sync functions run in a separate thread
        },
    )

    for func_name, func in getmembers(env, isfunction):
        assert func_name not in service_config
        service_config[func_name] = func

    await server.register_service(service_config)

    logger.info(f"{service_name} service registered at workspace: {server.config.workspace}")


class ImportCollector(ast.NodeVisitor):
    def __init__(self):
        self.imported: List[str] = []

    def visit_Import(self, node: ast.Import):
        raise ValueError("Found 'import' statement. Expected 'from .<local module> import <func>' only")

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if not node.level:
            raise ValueError(f"Unsupported absolute import from {node.module}")

        if "." in node.module:
            raise ValueError(f"Unsupported nested import from {node.module}")

        for alias_node in node.names:
            self.imported.append(alias_node.name)
            if alias_node.asname is not None:
                raise ValueError(
                    f"Please import workflow functions without 'as', i.e. use '{alias_node.name}' instead of '{alias_node.asname}'."
                )


class RemoteSubmodule:
    def __init__(self, env_name: str):
        self.server_url = get_server_url(env_name)
        self.env_name = env_name
        self.conda_env_name = get_conda_env_name(env_name)
        self.contrib = None
        local_src = Path(__file__).parent.parent / "envs" / env_name / "local.py"
        tree = get_ast_tree(local_src)
        import_collector = ImportCollector()
        import_collector.visit(tree)
        self.__all__ = import_collector.imported
        self.service_funcs = {}
        self.server_proc: Optional[subprocess.Popen] = None
        self.service_procs = set()

        def terminate_procs():
            for sp in self.service_procs:
                try:
                    sp.terminate()
                except Exception as e:
                    warnings.warn(str(e))
                    try:
                        sp.kill()
                    except Exception as ee:
                        warnings.warn(str(ee))

            if self.server_proc is not None:
                try:
                    self.server_proc.terminate()
                except Exception as e:
                    warnings.warn(str(e))
                    self.server_proc.kill()

            atexit.register(terminate_procs)

        for name in self.__all__:
            setattr(self, name, partial(self._service_call, _contrib_func_name=name))

    def __await__(self):
        yield from self._ainit().__await__()

    async def _ainit(self):
        try:
            server = await connect_to_server({"server_url": self.server_url})
        except Exception as e:
            error_msg = (
                f"Failed to connect to {self.server_url} {{details}}."
                f"\nMake sure {get_env_specific_server_url_var_name(self.env_name)} or {SERVER_URL_VAR_NAME} "
                f"are set or {self.server_url} is available."
            )
            if self.server_url.startswith("http://localhost:") and AUTOSTART_SERVER:
                print("preparing to autostart server")
                port = int(self.server_url[len("http://localhost:") :])
                check_env_cmd = f"conda run -n {self.conda_env_name} python --version"
                print(f"checking if {self.conda_env_name} exists: {check_env_cmd}")
                ret = subprocess.run(check_env_cmd, shell=True, check=False)
                if ret.returncode != 0:
                    print(f"missing conda env: {self.conda_env_name}")
                    if AUTOINSTALL_SUBMODULE_ENVS:
                        create_env_cmd = (
                            f"mamba env create -f "
                            f"{Path(__file__).parent.parent / 'static' / 'envs' / f'{self.env_name}.yaml'}"
                        )
                        print(f"creating conda env {self.conda_env_name}: {create_env_cmd}")
                        subprocess.run(
                            create_env_cmd,
                            shell=True,
                            check=True,
                        )

                    subprocess.run(check_env_cmd, shell=True, check=True)

                server_cmd = (
                    f"conda run -n {self.conda_env_name} "
                    f"python -m bioimageio.workflows.server start-server --host=0.0.0.0 --port={port}"
                )
                print(f"starting server: {server_cmd}")
                self.server_proc = subprocess.Popen(
                    server_cmd,
                    shell=True,
                )
                try:
                    server = await connect_to_server({"server_url": self.server_url})
                except Exception as e2:
                    raise Exception(error_msg.format(details="after autostarting it")) from e2
            else:
                raise Exception(error_msg.format(details="")) from e

        try:
            submodule_service = await server.get_service(f"bioimageio-wf-service-{self.env_name}")
        except Exception as e:
            raise Exception(
                f"bioimageio-{self.env_name} service not found. Start with 'python -m bioimageio.workflows.server "
                f"{self.env_name}' in a suitable (conda) environment."
            ) from e

        self.service_funcs = {name: getattr(submodule_service, name) for name in self.__all__}
        return self

    async def _service_call(self, *args, _contrib_func_name, **kwargs):
        await self
        return await self.service_funcs[_contrib_func_name](*args, **kwargs)
