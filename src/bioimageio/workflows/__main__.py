import json
import warnings
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from functools import partial
from typing import Optional, Union

import typer
from bioimageio.core import load_resource_description
from bioimageio.core.__main__ import app, help_version as help_version_core
from bioimageio.core.image_helper import load_image, save_image
from bioimageio.core.resource_io.nodes import ResourceDescription, Workflow
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
    workflow_rdf: str = typer.Argument(None, help="BioImage.IO workflow RDF id/url/path."),
    *,
    output_folder: Path = Path("outputs"),
    output_tensor_extension: str = ".npy",
    help: bool = typer.Option(False, "--help", "-h"),
    ctx: typer.Context,
):
    """Run a BioImage.IO workflow."""
    if workflow_rdf is None:
        wf: Optional[ResourceDescription] = None
        wf_name = "BioImage.IO workflow"
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # ignore warnings for loading workflow as we do not develop the wf here.
            wf = load_resource_description(workflow_rdf)

        if not isinstance(wf, Workflow):
            type_ = wf.type if wf.type != "workflow" else type(wf)
            raise ValueError(f"Expected workflow RDF, but got type {type_}.")

        assert isinstance(wf, Workflow)

        wf_name = wf.name

    parser = ArgumentParser(description=f"CLI to run {wf_name}", formatter_class=ArgumentDefaultsHelpFormatter)

    # replicate typer args to show up in help
    parser.add_argument(
        metavar="workflow-rdf",
        dest="workflow_rdf",
        help="BioImage.IO workflow RDF id/url/path.",
    )
    group = parser.add_argument_group(
        "general options", "options for the 'run-workflow' command, not the workflow to be run."
    )
    group.add_argument(
        "--output-folder", dest="output_folder", help="Folder to save outputs to.", default=Path("outputs")
    )
    group.add_argument(
        "--output-tensor-extension",
        dest="output_tensor_extension",
        help="Determines how to save output tensors.",
        default=".npy",
    )

    def add_param_args(params, group):
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

            if hasattr(param, "default"):
                argument_kwargs["default"] = param.default
                argument_kwargs["metavar"] = param.name[0].capitalize()
            else:
                argument_kwargs["metavar"] = param.name

            if param.type == "list":
                argument_kwargs["nargs"] = "*"

            arg_name = ("--" if "default" in argument_kwargs else "") + param.name.replace("_", "-")
            group.add_argument(arg_name, **argument_kwargs)

    def prepare_parameter(value, param: Union[Input, Option]):
        if param.type == "tensor":
            return load_image(value, [a.name or a.type for a in param.axes])
        else:
            return value

    if wf is not None:
        add_param_args(wf.inputs, parser.add_argument_group(f"inputs of '{wf_name}'"))
        add_param_args(wf.options, parser.add_argument_group(f"options of '{wf_name}'"))

    given_args = ["--output-folder", str(output_folder), "--output-tensor-extension", output_tensor_extension] + list(
        ctx.args
    )
    if help:
        given_args.append("--help")

    if workflow_rdf is not None:
        given_args.insert(0, workflow_rdf)

    args = parser.parse_args(given_args)
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
