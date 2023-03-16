from typing import Optional

import xarray as xr


async def hello(msg: str = "Hello!", tensor: Optional[xr.DataArray] = None) -> str:
    """dummy workflow printing msg

    This dummy workflow is intended as a demonstration and for testing.

    .. code-block:: yaml
    authors: [{name: Fynn Beuttenmüller, github_user: fynnbe, affiliation: EMBL Heidelberg}]
    cite: [{text: BioImage.IO, url: "https://doi.org/10.1101/2022.06.07.495102"}]
    tags: [demo]
    covers: ["https://github.com/bioimage-io/bioimage.io/raw/10db0410b15684cdeac19d795b0edb330a3a7b80/public/static/img/bioimage-io-icon.png"]

    Args:
        msg: Message
        tensor: tensor whose shape is added to message
            axes:
            - type: batch
            - type: space
              name: x
              description: demo space x
              unit: millimeter
              step: 1.5
            - type: index
              name: demo index
              description: a special index axis

    Returns:
        msg. A message, optionally enriched with the tensor shape.
    """
    if tensor is not None:
        msg += f" The tensor shape is {tensor.shape}"

    print(msg)
    return msg
