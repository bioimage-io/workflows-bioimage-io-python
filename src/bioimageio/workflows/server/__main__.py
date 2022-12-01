import argparse

from hypha.server import get_argparser as get_hypha_arg_parser, start_server as start_hypha_server


def start_server(args):
    start_hypha_server(args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="bioimageio.workflows.server")
    subparsers = parser.add_subparsers(help="sub-command help")

    # create the parser for the "a" command
    parser_start_server = subparsers.add_parser(
        "start-server", help="Start a hypha server", parents=[get_hypha_arg_parser()]
    )
    parser_start_server.set_defaults(func=start_server)

    # # create the parser for the "b" command
    # parser_b = subparsers.add_parser('b', help='b help')
    # parser_b.add_argument('--baz', choices='XYZ', help='baz help')

    args = parser.parse_args()
    args.func(args)
