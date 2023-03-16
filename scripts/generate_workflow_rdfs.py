import collections.abc
import inspect
import sys
import types
import typing
import warnings
from argparse import ArgumentParser
from importlib import import_module
from pathlib import Path
from typing import Literal, get_args, get_origin

import docstring_parser
import numpy as np
import xarray as xr
from marshmallow import missing
from marshmallow.utils import _Missing

import bioimageio.spec.workflow.schema as wf_schema
import bioimageio.workflows.envs
from bioimageio.spec import load_raw_resource_description, serialize_raw_resource_description_to_dict
from bioimageio.spec.shared import field_validators, fields, yaml
from bioimageio.spec.workflow.raw_nodes import (
    Axis,
    Input,
    Option,
    Output,
    TYPE_NAMES,
    UnknownAxes,
    Workflow as WorkflowRawNode,
)
from bioimageio.workflows import CURRENT_VERSION

TYPE_NAME_MAP = {**TYPE_NAMES, **{xr.DataArray: "tensor", np.ndarray: "tensor"}}
UNKNOWN_AXES = get_args(UnknownAxes)

# keep this axes_field in sync with wf_schema.Workflow.axes
axes_field = fields.Union(
    [
        fields.List(fields.Nested(wf_schema.Axis())),
        fields.String(
            validate=field_validators.OneOf(get_args(UnknownAxes)),
        ),
    ],
)


def get_type_name(annotation):
    orig = get_origin(annotation)
    if orig is list or orig is tuple or orig is collections.abc.Sequence:
        annotation = list
    elif orig is dict or orig is collections.OrderedDict:
        annotation = dict
    elif orig is typing.Union:
        args = get_args(annotation)
        args = [a for a in args if a is not type(None)]
        assert args
        annotation = get_type_name(args[0])  # use first type in union annotation
    elif orig is Literal:
        args = get_args(annotation)
        assert args
        annotation = get_type_name(type(args[0]))  # use type of first literal

    if isinstance(annotation, str):
        assert annotation in TYPE_NAME_MAP.values(), annotation
        return annotation
    else:
        return TYPE_NAME_MAP[annotation]


def parse_args():
    p = ArgumentParser(description="Generate workflow RDFs for one workflow environment submodule")
    p.add_argument("env_name", choices=[c for c in dir(bioimageio.workflows.envs) if not c.startswith("_")])
    p.add_argument(
        "--verify", action="store_true", help="raise error if generating would change any existing (or missing) file."
    )

    return p.parse_args()


class WorkflowSignature(inspect.Signature):
    pass


def extract_axes_from_param_descr(
    descr: str,
) -> typing.Tuple[str, typing.Union[_Missing, UnknownAxes, typing.List[Axis]]]:
    if "\n" in descr:
        descr, *axes_descr_lines = descr.split("\n")
        assert axes_descr_lines[0].strip().startswith("axes:")
        if len(axes_descr_lines) == 1:
            axes_descr = axes_descr_lines[0][len("axes:") :]
        else:
            axes_descr = "\n".join(axes_descr_lines[1:])

        try:
            axes_data = yaml.load(axes_descr)
            axes = axes_field._deserialize(axes_data)
        except Exception as e:
            raise ValueError("Invalid axes description") from e
    else:
        axes = missing

    return descr, axes


def extract_serialized_wf_kwargs(descr: str) -> typing.Tuple[str, typing.Dict[str, typing.Any]]:
    separator = ".. code-block:: yaml"
    if separator in descr:
        descr, kwarg_descr = descr.split(separator)
        try:
            kwargs = yaml.load(kwarg_descr)
        except Exception as e:
            raise ValueError("Invalid additional fields") from e
    else:
        kwargs = {}

    # remove any indentation and new lines in the description, while keeping two new lines as one.
    lines = [line.strip() for line in descr.strip().split("\n")]
    descr = " ".join([line or "\n" for line in lines])

    kwargs["tags"] = kwargs.get("tags", [])
    if "workflow" not in kwargs["tags"]:
        kwargs["tags"].insert(0, "workflow")

    if "bioimageio.workflows" not in kwargs["tags"]:
        kwargs["tags"].insert(0, "bioimageio.workflows")

    kwargs["cite"] = kwargs.get("cite", [])
    if "BioImage.IO" not in [c["text"] for c in kwargs["cite"]]:
        kwargs["cite"].insert(0, dict(text="BioImage.IO", url="https://doi.org/10.1101/2022.06.07.495102"))

    return descr, kwargs


def main(env_name: str, verify: bool):
    dist = Path(__file__).parent / "../src/bioimageio/workflows/static/workflow_rdfs"
    if not verify:
        dist.mkdir(parents=True, exist_ok=True)

    local_submodule = import_module(f"bioimageio.workflows.envs.{env_name}.local")
    for wf_id in dir(local_submodule):
        wf_func = getattr(local_submodule, wf_id)
        if not isinstance(wf_func, types.FunctionType):
            if not wf_id.startswith("_"):
                warnings.warn(f"ignoring non-function {wf_id}")

            continue

        doc = docstring_parser.parse(wf_func.__doc__)

        param_descriptions = {param.arg_name: param.description for param in doc.params}
        inputs = []
        options = []
        sig = WorkflowSignature.from_callable(wf_func)
        assert sig.return_annotation is not inspect.Signature.empty
        for name, param in sig.parameters.items():
            type_name = get_type_name(param.annotation)
            descr = param_descriptions[name]
            if type_name == "tensor":
                descr, axes = extract_axes_from_param_descr(descr)
                if axes is missing:
                    raise ValueError(
                        f"Missing axes description in description of parameter '{name}' of workflow '{wf_id}'.\n"
                        f"Change\n    {name}: <description> \nto \n    {name}: <description>\n        axes: unknown\n"
                        "or\n"
                        f"    {name}: <description>\n"
                        f"        axes:\n"
                        "        - type: batch\n"
                        "        - type: channel\n"
                        "          name: ...\n"
                        "        ...\n"
                        f"find format details at: "
                        "https://github.com/bioimage-io/spec-bioimage-io/blob/gh-pages/workflow_spec_latest.md#inputs:axes"
                    )
            else:
                axes = missing

            if param.default is inspect.Parameter.empty:
                inputs.append(Input(name=name, description=descr, type=type_name, axes=axes))
            else:
                default_value: typing.Any = param.default
                if isinstance(default_value, tuple):
                    default_value = list(default_value)

                options.append(Option(name=name, description=descr, type=type_name, axes=axes, default=default_value))

        return_descriptions = {}
        for ret_descr in doc.returns.description.split("\n\n"):
            name, *remaining = ret_descr.split(".")
            return_descriptions[name.strip()] = ".".join(remaining).strip()

        outputs = []
        ret_annotations = sig.return_annotation
        ret_annotations_orig = get_origin(ret_annotations)
        if ret_annotations_orig in (typing.Tuple, tuple):
            ret_annotations = get_args(ret_annotations)
        else:
            ret_annotations = [ret_annotations]

        if len(return_descriptions) != len(ret_annotations):
            raise ValueError("number of documented return values does not match return annotation")

        for ret_type, (name, descr) in zip(ret_annotations, return_descriptions.items()):
            type_name = get_type_name(ret_type)
            if type_name == "tensor":
                descr, axes = extract_axes_from_param_descr(descr)
            else:
                axes = missing

            assert descr
            outputs.append(Output(name=name, description=descr, type=type_name, axes=axes))

        assert doc.long_description is not None
        description, serialized_kwargs = extract_serialized_wf_kwargs(doc.long_description)
        wf = WorkflowRawNode(
            name=doc.short_description,
            description=description,
            inputs=inputs,
            options=options,
            outputs=outputs,
            version=CURRENT_VERSION,
            id=f"bioimageio/{wf_id}",
            license="MIT",
            rdf_source=f"https://raw.githubusercontent.com/bioimage-io/workflows-bioimage-io-python/main/src/bioimageio/workflows/static/workflow_rdfs/{wf_id}.yaml",
            tags=["workflow"],
            icon="⚙",
        )
        serialized = serialize_raw_resource_description_to_dict(wf)
        serialized.update(serialized_kwargs)

        # round trip to ensure we will load the same workflow that we saved
        wf = load_raw_resource_description(serialized)
        serialized2 = serialize_raw_resource_description_to_dict(wf)
        assert serialized == serialized2

        path = (dist / wf_id).with_suffix(".yaml").resolve()
        if verify:
            with path.open("r", encoding="utf-8") as f:
                existing = yaml.load(f)

            if serialized != existing:
                raise RuntimeError(f"Exising {path} differs from generated RDF.")
        else:
            with path.open("w", encoding="utf-8") as f:
                yaml.dump(serialized, f)

            print(f"saved {path}")

        import json

        with path.with_suffix(".json").open("w", encoding="utf-8") as f:
            json.dump(serialized, f, ensure_ascii=False, indent=4, sort_keys=True)

    print("done")


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.env_name, args.verify))
