import ast
import asyncio
import atexit
import logging
import warnings
from functools import partial
from pathlib import Path
from typing import List

from bioimageio.workflows.server._utils import ensure_conda_env_exists, get_server
from bioimageio.workflows.server.env_vars import (
    AUTOSTART_SERVER,
    SERVER_CONDA_ENV,
    SERVER_URL,
    SERVER_URL_VAR_NAME,
    START_SUBMODULE_SERVICE_NAME,
    get_conda_env_name,
    get_env_service_name,
    get_env_specific_server_url_var_name,
    get_server_url,
)
from bioimageio.workflows.utils import get_ast_tree

logger = logging.getLogger(__name__)


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
        self.env_service_name = get_env_service_name(env_name)
        self.conda_env_name = get_conda_env_name(env_name)
        local_src = Path(__file__).parent.parent / "envs" / env_name / "local.py"
        tree = get_ast_tree(local_src)
        import_collector = ImportCollector()
        import_collector.visit(tree)
        self.__all__ = import_collector.imported
        self.service_funcs = {}
        self.procs = []

        def terminate_procs():
            for proc in self.procs[::-1]:
                try:
                    proc.terminate()
                except Exception as e:
                    warnings.warn(str(e))
                    try:
                        proc.kill()
                    except Exception as ekill:
                        warnings.warn(str(ekill))

        atexit.register(terminate_procs)

        for name in self.__all__:
            setattr(self, name, partial(self._service_call, _submodule_func_name=name))

    def __await__(self):
        yield from self._ainit().__await__()

    async def _ainit(self):
        try:
            server = await get_server(self.env_name)
        except Exception as e:
            error_msg = (
                f"Failed to connect to {self.server_url} {{details}}."
                f"\nMake sure {get_env_specific_server_url_var_name(self.env_name)} or {SERVER_URL_VAR_NAME} "
                f"are set or {self.server_url} is available."
            )
            if self.server_url.startswith("http://localhost:") and AUTOSTART_SERVER:
                if get_server_url(self.env_name) != SERVER_URL:
                    raise NotImplementedError(
                        f"Autostart server for submodule with dedicated server url. "
                        f"Start submodule service manually or unset "
                        f"{get_env_specific_server_url_var_name(self.env_name)}={self.server_url} "
                        f"to use default server url ({SERVER_URL}) for this submodule which allows for autostart."
                    )

                print("preparing to autostart server")
                ensure_conda_env_exists(SERVER_CONDA_ENV)
                port = int(self.server_url[len("http://localhost:") :])
                cmd = (
                    f"conda run -n {SERVER_CONDA_ENV} "
                    f"python -m bioimageio.workflows.server start-server --host=0.0.0.0 --port={port}"
                )
                print(f"starting server: {cmd}")
                assert not self.procs
                self.procs.append(
                    asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                )
                try:
                    server = await get_server("default")
                except Exception as e2:
                    raise Exception(error_msg.format(details="after autostarting it")) from e2

                # start submodule service launcher
                cmd = (
                    f"conda run -n {SERVER_CONDA_ENV} "
                    f"python -m bioimageio.workflows.server start-submodule-service-launcher"
                )
                print(f"starting submodule service launcher: {cmd}")
                self.procs.append(
                    asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                )
            else:
                raise Exception(error_msg.format(details="")) from e

        try:
            submodule_service = await server.get_service(self.env_service_name)
        except Exception:
            print(f"failed to get {self.env_service_name}. Attempting to start it...")
            launcher_service = await server.get_service(START_SUBMODULE_SERVICE_NAME)
            await launcher_service.start_submodule_service(self.env_name)
            submodule_service = await server.get_service(self.env_service_name)

        self.service_funcs = {name: submodule_service[name] for name in self.__all__}
        return self

    async def _service_call(self, *args, _submodule_func_name, **kwargs):
        await self
        print('calling ', _submodule_func_name)
        return await self.service_funcs[_submodule_func_name](*args, **kwargs)
