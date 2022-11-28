import ast
import asyncio
import logging
import os
from functools import partial
from inspect import getmembers, isfunction
from pathlib import Path
from typing import List, Optional

from imjoy_rpc.hypha import connect_to_server

from bioimageio.workflows import envs
from bioimageio.workflows.server import DEFAULT_SERVER_URL, SERVER_URL_VAR_NAME
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
        id=f"bioimageio-workflows-{env_name}",
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


def get_env_specific_server_url_var_name(env_name) -> str:
    return f"BIOIMAGEIO_WORKFLOWS_{env_name.upper()}_URL"


def get_server_url(env_name) -> str:
    return os.getenv(get_env_specific_server_url_var_name(env_name), os.getenv(SERVER_URL_VAR_NAME, DEFAULT_SERVER_URL))


class RemoteSubmodule:
    def __init__(self, env_name: str, server_url: Optional[str] = None):
        self.server_url = server_url or get_server_url(env_name)
        self.env_name = env_name
        self.contrib = None
        local_src = Path(__file__).parent.parent / "envs" / env_name / "local.py"
        tree = get_ast_tree(local_src)
        import_collector = ImportCollector()
        import_collector.visit(tree)
        self.__all__ = import_collector.imported
        self.service_funcs = {}
        for name in self.__all__:
            setattr(self, name, partial(self._service_call, _contrib_func_name=name))

    def __await__(self):
        yield from self._ainit().__await__()

    async def _ainit(self):
        try:
            server = await asyncio.create_task(connect_to_server({"server_url": self.server_url}))
        except Exception as e:
            raise Exception(
                f"Failed to connect to {self.server_url}. "
                f"Make sure {get_env_specific_server_url_var_name(self.env_name)} or {SERVER_URL_VAR_NAME} "
                f"is set or {self.server_url} is available."
            ) from e
        try:
            contrib_service = await server.get_service(f"bioimageio-workflows-{self.env_name}")
        except Exception as e:
            raise Exception(
                f"bioimageio-{self.env_name} service not found. Start with 'python -m bioimageio.core.contrib.{self.env_name}' in a suitable (conda) environment."
            ) from e
            # todo: start contrib service entry point, e.g. f"bioimageio start {env_name}"

        self.service_funcs = {name: getattr(contrib_service, name) for name in self.__all__}
        return self

    async def _service_call(self, *args, _contrib_func_name, **kwargs):
        await self
        return await self.service_funcs[_contrib_func_name](*args, **kwargs)
