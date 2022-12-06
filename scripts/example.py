import asyncio

from bioimageio.core import load_resource_description
from bioimageio.core.image_helper import load_image
from bioimageio.core.resource_io.nodes import Model
from bioimageio.spec.shared import resolve_source
from bioimageio.workflows import stardist_prediction_2d, hello


async def main():
    print(await hello())

    rdf = "chatty-frog"
    model = load_resource_description("chatty-frog")
    assert isinstance(model, Model)
    # expected_labels = load_image(
    #     resolve_source("https://zenodo.org/record/7372477/files/stardist_chatty_frog_labels.npy"), tuple("byx")
    # )

    raw = load_image(model.test_inputs[0], model.inputs[0].axes)
    labels, polys = await stardist_prediction_2d(rdf, raw, tiles=None)

    print("labels", labels.shape)


if __name__ == "__main__":
    asyncio.run(main())
