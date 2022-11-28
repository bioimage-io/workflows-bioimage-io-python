import pytest
from numpy.testing import assert_array_equal

from bioimageio.core import load_resource_description
from bioimageio.core.image_helper import load_image
from bioimageio.core.resource_io.nodes import Model
from bioimageio.spec.shared import resolve_source


@pytest.mark.parametrize("tiles", [None])
@pytest.mark.asyncio
async def test_stardist_2d(tiles):
    from bioimageio.workflows import run_stardist_inference_2d

    rdf = "chatty-frog"
    model = load_resource_description("chatty-frog")
    assert isinstance(model, Model)
    expected_labels = load_image(
        resolve_source("https://zenodo.org/record/7372477/files/stardist_chatty_frog_labels.npy"), tuple("byx")
    )

    raw = load_image(model.test_inputs[0], model.inputs[0].axes)
    labels, polys = await run_stardist_inference_2d(rdf, raw, tiles=tiles)

    assert_array_equal(labels, expected_labels)
