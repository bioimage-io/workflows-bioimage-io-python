import tempfile
from math import ceil
from os import PathLike
from pathlib import Path
from typing import Dict, IO, List, Optional, Sequence, Tuple, Union

import xarray as xr
from stardist import import_bioimageio as stardist_import_bioimageio

from bioimageio.core import export_resource_package, load_resource_description
from bioimageio.core.prediction_pipeline._combined_processing import CombinedProcessing
from bioimageio.core.prediction_pipeline._measure_groups import compute_measures
from bioimageio.core.resource_io.nodes import Model
from bioimageio.spec.model import raw_nodes
from bioimageio.spec.shared.raw_nodes import ResourceDescription as RawResourceDescription


async def run_stardist_inference_2d(
    model_rdf: Union[str, PathLike, dict, IO, bytes, raw_nodes.URI, RawResourceDescription],
    input_tensor: xr.DataArray,
    tiles: Optional[Sequence[Dict[str, int]]] = None,
) -> Tuple[xr.DataArray, dict]:
    """run stardist model inference

    A workflow to apply a stardist model and the stardist postprocessing.
    This workflow is loosely based on https://nbviewer.org/github/stardist/stardist/blob/master/examples/2D/3_prediction.ipynb

    .. code-block:: yaml
    authors: [{name: Fynn Beuttenmüller, github_user: fynnbe}]
    cite:
    - text: BioImage.IO
      doi: 10.1101/2022.06.07.495102
    - text: "Stardist: Cell Detection with Star-Convex Polygons"
      doi: 10.1007/978-3-030-00934-2_30
    - text: "Stardist: Star-convex Polyhedra for 3D Object Detection and Segmentation in Microscopy"
      doi: 10.1109/WACV45572.2020.9093435

    Args:
        model_rdf: the (source/raw) model RDF that describes the stardist model to be used for inference
        input_tensor: raw input
            axes:
            - type: batch
            - type: channel
            - type: space
              name: y
            - type: space
              name: x
        tiles: Tile shapes for model inputs. Defaults to no tiling.

    Returns:
        labels. Labels of detected objects
            axes:
            - type: batch
            - type: space
              name: y
            - type: space
              name: x

        polys. Dictionary describing the labeled object's polygons
    """

    # todo: use run_model_inference_with_dask for model inference and then apply stardist postprocessing.
    # outputs = await run_model_inference_with_dask(model_rdf, input_tensor, boundary_mode=boundary_mode, enable_preprocessing=enable_preprocessing, enable_postprocessing=True, tiles=tiles)
    # assert len(outputs) == 1
    # output = outputs["output"]

    package_path = export_resource_package(model_rdf)
    with tempfile.TemporaryDirectory() as tmp_dir:
        import_dir = Path(tmp_dir) / "import_dir"
        imported_stardist_model = stardist_import_bioimageio(package_path, import_dir)

    # transpose tensors to match ipt spec
    model = load_resource_description(package_path)
    assert isinstance(model, Model)
    if len(model.inputs) != 1:
        raise NotImplementedError("Multiple inputs for stardist models not yet implemented")

    if len(model.outputs) != 1:
        raise NotImplementedError("Multiple outputs for stardist models not yet implemented")

    if tiles is None:
        n_tiles: Optional[List[int]] = None
    else:
        n_tiles = []
        for i, a in enumerate(model.inputs[0].axes):
            t = tiles[i][a]
            s = input_tensor.sizes[a]
            n_tiles.append(max(ceil(s / t), 1))

    prep = CombinedProcessing.from_tensor_specs(model.inputs)
    ipt_name = model.inputs[0].name
    sample = {ipt_name: input_tensor}
    computed_measures = compute_measures(prep.required_measures, sample=sample)
    prep.apply(sample, computed_measures)

    img = sample[ipt_name].transpose(*model.inputs[0].axes).to_numpy()
    labels, polys = imported_stardist_model.predict_instances(
        img,
        axes="".join([{"b": "S"}.get(a[0], a[0].capitalize()) for a in model.inputs[0].axes]),
        n_tiles=n_tiles,
    )

    if len(labels.shape) == 2:  # batch dim got squeezed
        labels = labels[None]

    output_axes_wo_channels = tuple(a for a in model.outputs[0].axes if a != "c")
    assert output_axes_wo_channels == tuple("byx")
    return xr.DataArray(labels, dims=output_axes_wo_channels), polys
