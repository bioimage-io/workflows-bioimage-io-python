import asyncio

from bioimageio.core import load_resource_description
from bioimageio.core.image_helper import load_image
from bioimageio.core.resource_io.nodes import Model
from bioimageio.workflows import hello, stardist_prediction_2d


async def main():
    print(await hello())

    rdf = "chatty-frog"

    # load test input from model
    model = load_resource_description(rdf)
    assert isinstance(model, Model)
    raw = load_image(model.test_inputs[0], model.inputs[0].axes)

    # call env specific workflow
    labels, polys = await stardist_prediction_2d(rdf, raw)

    print("labels", labels.shape)


if __name__ == "__main__":
    asyncio.run(main())
