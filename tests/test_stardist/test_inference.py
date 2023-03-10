import pytest
from numpy.testing import assert_array_equal

from bioimageio.core import load_resource_description
from bioimageio.core.image_helper import load_image
from bioimageio.core.resource_io.nodes import Model
from bioimageio.spec.shared import resolve_source
from bioimageio.spec.shared.common import AXIS_LETTER_TO_NAME


@pytest.mark.parametrize("tile", [None, {"batch": 1, "channel": 1, "x": 100, "y": 100}])
@pytest.mark.asyncio
async def test_stardist_prediction_2d(tile):
    from bioimageio.workflows import stardist_prediction_2d

    rdf = "chatty-frog"
    model = load_resource_description("chatty-frog")
    assert isinstance(model, Model)
    expected_labels = load_image(
        resolve_source("https://zenodo.org/record/7372477/files/stardist_chatty_frog_labels.npy"), ("batch", "y", "x")
    )

    raw = load_image(model.test_inputs[0], [AXIS_LETTER_TO_NAME.get(a, a) for a in model.inputs[0].axes]).transpose(
        "batch", "channel", "y", "x"
    )
    labels, polys = await stardist_prediction_2d(rdf, raw, tile=tile)

    assert_array_equal(labels, expected_labels)
