import json
from argparse import ArgumentParser
from functools import partial
from typing import Union

import typer

from bioimageio.core import load_resource_description
from bioimageio.core.__main__ import app, help_version as help_version_core
from bioimageio.core.image_helper import load_image, save_image
from bioimageio.core.resource_io.nodes import Workflow
from bioimageio.spec.workflow.raw_nodes import Input, Option, TYPE_NAME_TYPES
from bioimageio.workflows import __version__
from bioimageio.workflows.operators import run_workflow as run_workflow_op

try:
    from typing import get_args
except ImportError:
    from typing_extensions import get_args  # type: ignore

from pathlib import Path


# extend help/version string by workflow version
help_version_workflows = f"bioimageio.workflows {__version__}"
help_version = f"{help_version_core}\n{help_version_workflows}"
# prevent rewrapping with \b\n: https://click.palletsprojects.com/en/7.x/documentation/#preventing-rewrapping
app.info.help = "\b\n" + help_version


@app.callback()
def callback():
    typer.echo(help_version)


# @app.command
# def run_submodule_services(*env_name: str):
#     distributed.run_submodule_services(*env_name)


@app.command(context_settings=dict(allow_extra_args=True, ignore_unknown_options=True), add_help_option=False)
def run_workflow(
    workflow_rdf: str = typer.Argument(..., help="BioImage.IO workflow RDF id/url/path."),
    *,
    output_folder: Path = Path("outputs"),
    output_tensor_extension: str = ".npy",
    ctx: typer.Context,
):
    """Run a BioImage.IO workflow. ('--help' only available with WORKFLOW_RDF specified)"""  # todo: improve --help
    wf = load_resource_description(workflow_rdf)
    if not isinstance(wf, Workflow):
        type_ = wf.type if wf.type != "workflow" else type(wf)
        raise ValueError(f"Expected workflow RDF, but got type {type_}.")

    assert isinstance(wf, Workflow)
    parser = ArgumentParser(description=f"CLI for {wf.name}")

    # replicate typer args to show up in help
    parser.add_argument(
        metavar="rdf-source",
        dest="workflow_rdf",
        help="BioImage.IO workflow RDF id/url/path. The optional arguments below are workflow specific.",
    )
    parser.add_argument(
        metavar="output-folder", dest="output_folder", help="Folder to save outputs to.", default=Path("outputs")
    )
    parser.add_argument(
        metavar="output-tensor-extension",
        dest="output_tensor_extension",
        help="Output tensor extension.",
        default=".npy",
    )

    def add_param_args(params):
        for param in params:
            argument_kwargs = {}
            argument_kwargs["help"] = param.description or ""
            if param.type == "tensor":
                if param.axes == "unknown":
                    raise ValueError(
                        f"Workflows may not define input or output tensors with unknown axes ({param.name})"
                    )
                ax = [a.name or a.type for a in param.axes]
                argument_kwargs["help"] += f" (axes: {','.join(ax)})"
                argument_kwargs["type"] = partial(load_image, axes=ax)
            else:
                argument_kwargs["type"] = TYPE_NAME_TYPES[param.type]

            if param.type == "list":
                argument_kwargs["nargs"] = "*"

            if hasattr(param, "default"):
                argument_kwargs["default"] = param.default
            else:
                argument_kwargs["required"] = True

            argument_kwargs["metavar"] = param.name[0].capitalize()
            parser.add_argument("--" + param.name.replace("_", "-"), **argument_kwargs)

    def prepare_parameter(value, param: Union[Input, Option]):
        if param.type == "tensor":
            return load_image(value, [a.name or a.type for a in param.axes])
        else:
            return value

    add_param_args(wf.inputs)
    add_param_args(wf.options)
    args = parser.parse_args([workflow_rdf, str(output_folder), output_tensor_extension] + list(ctx.args))
    outputs = run_workflow_op(
        workflow_rdf,
        inputs=[prepare_parameter(getattr(args, ipt.name), ipt) for ipt in wf.inputs],
        options={opt.name: prepare_parameter(getattr(args, opt.name), opt) for opt in wf.options},
    )
    output_folder.mkdir(parents=True, exist_ok=True)
    for out_spec, (name, out) in zip(wf.outputs, outputs.items()):
        assert out_spec.name == name
        out_path = output_folder / name
        if out_spec.type == "tensor":
            save_image(out_path.with_suffix(output_tensor_extension), out)
        else:
            with out_path.with_suffix(".json").open("w") as f:
                json.dump(out, f)


if __name__ == "__main__":
    app()
