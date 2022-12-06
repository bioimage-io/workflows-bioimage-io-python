import argparse
import asyncio
from typing import Optional

from bioimageio.workflows.server import register_submodule_service, register_submodule_service_launcher

get_hypha_arg_parser: Optional[callable]
try:
    from hypha.server import get_argparser as get_hypha_arg_parser
except ImportError as e:
    get_hypha_arg_parser = None


def start_server(args):
    from hypha.server import start_server as start_hypha_server

    start_hypha_server(args)


async def start_submodule_service_launcher(_):
    await register_submodule_service_launcher()


async def start_submodule_service(args):
    await register_submodule_service(args.submodule_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="bioimageio.workflows.server")
    subparsers = parser.add_subparsers(help="sub-command help")

    if get_hypha_arg_parser is None:
        start_server_parser_parents = []
    else:
        start_server_parser_parents = [get_hypha_arg_parser()]

    parser_start_server = subparsers.add_parser(
        "start-server",
        help="Start a hypha server to register submodule services with.",
        parents=start_server_parser_parents,
        add_help=False,
    )
    parser_start_server.set_defaults(func=start_server)

    parser_start_submodule_service_launcher = subparsers.add_parser(
        "start-submodule-service-launcher",
        help="Start the service that can start a bioimageio workflow environment service providing environment specific functionality. "
        "Expects a running server. Uses start-submodule-service on server side.",
    )
    parser_start_submodule_service_launcher.set_defaults(func=start_submodule_service_launcher)

    parser_start_submodule_service = subparsers.add_parser(
        "start-submodule-service",
        help="Start a bioimageio workflow environment service providing environment specific functionality. "
        "Needs to be called from a compatible conda environment."
        "Expects a running server.",
    )
    parser_start_submodule_service.set_defaults(func=start_submodule_service)
    parser_start_submodule_service.add_argument(
        metavar="submodule-name", dest="submodule_name", help="submodule name, e.g. 'stardist'"
    )

    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    loop.create_task(args.func(args))
    loop.run_forever()

