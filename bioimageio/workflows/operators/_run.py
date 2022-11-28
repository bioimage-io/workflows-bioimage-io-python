from dataclasses import dataclass
from os import PathLike
from typing import Any, Dict, IO, OrderedDict, Sequence, Union

import xarray as xr
from marshmallow import missing

import bioimageio.workflows
from bioimageio.core import load_resource_description
from bioimageio.core.resource_io import nodes
from bioimageio.spec import load_raw_resource_description
from bioimageio.spec.model import raw_nodes
from bioimageio.spec.shared.raw_nodes import ResourceDescription as RawResourceDescription
from bioimageio.spec.workflow.raw_nodes import Workflow
from bioimageio.workflows import CURRENT_VERSION, Version

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


def run_workflow(
    workflow_rdf: Union[str, PathLike, dict, raw_nodes.URI, RawResourceDescription, IO, bytes],
    inputs: Union[Sequence, Dict[str, Any]] = tuple(),
    options: Dict[str, Any] = None,
) -> OrderedDict[str, Any]:
    """Run `workflow_rdf` with `inputs` and `options`."""
    wf = load_raw_resource_description(workflow_rdf)
    assert isinstance(wf, Workflow)
    wf_id = wf.id
    if wf_id.startswith("bioimageio/"):
        wf_id = wf_id[len("bioimageio/") :]

    wf_func_name, *wf_id_rest = wf_id.split("/")
    if len(wf_id_rest) > 1:
        raise ValueError(
            f"Got unexpected workflow id {wf.id}. Expected '[bioimageio/]<workflow function name>[/<bioimageio.workflows version>]'"
        )
    elif wf_id_rest:
        wf_version = Version(wf_id_rest[0])
    else:
        wf_version = CURRENT_VERSION  # default to current version

    if wf_version == CURRENT_VERSION:
        workflows = bioimageio.workflows
    else:
        raise NotImplementedError("ask hypha server to provide an appropriate env")

    outputs = tuple()
    for state in _iterate_workflow_steps_impl(rdf_source, test_steps=False, inputs=inputs, options=options):
        outputs = state.outputs

    return outputs

    workflow = load_resource_description(rdf_source)
    assert isinstance(workflow, nodes.Workflow)
    wf_options: Dict[str, Any] = {opt.name: opt.default for opt in workflow.options_spec}
    if test_steps:
        assert not inputs
        assert not options
        wf_inputs: Dict[str, Any] = {}
        steps = workflow.test_steps
    else:
        if not len(workflow.inputs_spec) == len(inputs):
            raise ValueError(f"Expected {len(workflow.inputs_spec)} inputs, but got {len(inputs)}.")

        wf_inputs = {ipt_spec.name: ipt for ipt_spec, ipt in zip(workflow.inputs_spec, inputs)}
        for k, v in options.items():
            if k not in wf_options:
                raise ValueError(f"Got unknown option {k}, expected one of {set(wf_options)}.")

            wf_options[k] = v

        steps = workflow.steps

    named_outputs = {}  # for later referencing

    def map_ref(value):
        assert isinstance(workflow, nodes.Workflow)
        if isinstance(value, str) and value.startswith("${{") and value.endswith("}}"):
            ref = value[4:-2].strip()
            if ref.startswith("self.inputs."):
                ref = ref[len("self.inputs.") :]
                if ref not in wf_inputs:
                    raise ValueError(f"Invalid workflow input reference {value}.")

                return wf_inputs[ref]
            elif ref.startswith("self.options."):
                ref = ref[len("self.options.") :]
                if ref not in wf_options:
                    raise ValueError(f"Invalid workflow option reference {value}.")

                return wf_options[ref]
            elif ref == "self.rdf_source":
                assert workflow.rdf_source is not missing
                return str(workflow.rdf_source)
            elif ref in named_outputs:
                return named_outputs[ref]
            else:
                raise ValueError(f"Invalid reference {value}.")
        else:
            return value

    # implicit inputs to a step are the outputs of the previous step.
    # For the first step these are the workflow inputs.
    outputs = tuple(inputs)
    for step in steps:
        if not hasattr(ops, step.op):
            raise NotImplementedError(f"{step.op} not implemented in {ops}")

        op = getattr(ops, step.op)
        if step.inputs is missing:
            inputs = outputs
        else:
            inputs = tuple(map_ref(ipt) for ipt in step.inputs)

        assert isinstance(inputs, tuple)
        options = {k: map_ref(v) for k, v in (step.options or {}).items()}
        outputs = op(*inputs, **options)
        if not isinstance(outputs, tuple):
            outputs = (outputs,)

        if step.outputs:
            assert step.id is not missing
            if len(step.outputs) != len(outputs):
                raise ValueError(
                    f"Got {len(step.outputs)} step output name{'s' if len(step.outputs) > 1 else ''} ({step.id}.outputs), "
                    f"but op {step.op} returned {len(outputs)} outputs."
                )

            named_outputs.update({f"{step.id}.outputs.{out_name}": out for out_name, out in zip(step.outputs, outputs)})

        yield WorkflowState(
            wf_inputs=wf_inputs, wf_options=wf_options, inputs=inputs, outputs=outputs, named_outputs=named_outputs
        )
    if len(workflow.outputs_spec) != len(outputs):
        raise ValueError(f"Expected {len(workflow.outputs_spec)} outputs from last step, but got {len(outputs)}.")

    def tensor_as_xr(tensor, axes: Sequence[nodes.Axis]):
        spec_axes = [a.name or a.type for a in axes]
        if isinstance(tensor, xr.DataArray):
            if list(tensor.dims) != spec_axes:
                raise ValueError(
                    f"Last workflow step returned xarray.DataArray with dims {tensor.dims}, but expected dims {spec_axes}."
                )

            return tensor
        else:
            return xr.DataArray(tensor, dims=tuple(spec_axes))

    outputs = tuple(
        tensor_as_xr(out, out_spec.axes) if out_spec.type == "tensor" else out
        for out_spec, out in zip(workflow.outputs_spec, outputs)
    )
    yield WorkflowState(
        wf_inputs=wf_inputs, wf_options=wf_options, inputs=inputs, outputs=outputs, named_outputs=named_outputs
    )
