import numpy as np
import pytest
from numpy.testing import assert_array_almost_equal

from bioimageio.core import load_raw_resource_description
from bioimageio.core.image_helper import load_image
from bioimageio.spec.model.raw_nodes import Model as RawModel


@pytest.mark.asyncio
async def test_inference_with_dask():
    from bioimageio.workflows.envs.default import inference_with_dask

    model = load_raw_resource_description(
        "https://raw.githubusercontent.com/bioimage-io/spec-bioimage-io/main/example_specs/models/upsample_test_model/rdf.yaml",
        update_to_format="latest",
    )
    assert isinstance(model, RawModel)

    test_inputs = [load_image(p, s.axes) for p, s in zip(model.test_inputs, model.inputs)]
    expected_outputs = [load_image(p, s.axes) for p, s in zip(model.test_outputs, model.outputs)]
    outputs = await inference_with_dask(
        model, test_inputs, tiles=[dict(zip(ipt.axes, ipt.shape.min)) for ipt in model.inputs]
    )
    # todo: adapt for multiple outputs
    halo = tuple(np.s_[h:-h] if h else np.s_[:] for h in model.outputs[0].halo)
    # use for debugging:
    outputs = [outputs[model.outputs[0].name].data.compute(scheduler="single-threaded")]
    for exp, act in zip(expected_outputs, outputs):
        assert_array_almost_equal(exp[halo], act[halo])
