import xarray as xr
import subprocess
from pathlib import Path

from imjoy_rpc.hypha import connect_to_server

from bioimageio.workflows.server.env_vars import AUTOINSTALL_SUBMODULE_ENVS, get_server_url


def ensure_conda_env_exists(conda_env_name: str) -> None:
    check_env_cmd = f"conda run -n {conda_env_name} python --version"
    print(f"checking if {conda_env_name} exists: {check_env_cmd}")
    ret = subprocess.run(check_env_cmd, shell=True, check=not AUTOINSTALL_SUBMODULE_ENVS)
    if ret.returncode != 0:
        assert AUTOINSTALL_SUBMODULE_ENVS
        create_env_cmd = "mamba env create -f " + str(Path(__file__).parent.parent / "static" / "envs" / "default.yaml")
        print(f"creating conda env {conda_env_name}: {create_env_cmd}")
        subprocess.run(
            create_env_cmd,
            shell=True,
            check=True,
        )
        subprocess.run(check_env_cmd, shell=True, check=True)


def encode_xarray(obj):
    assert isinstance(obj, xr.DataArray)
    return {
        "_rintf": True,
        "_rtype": "xarray",
        "data": obj.to_numpy(),
        "dims": obj.dims,
        "attrs": obj.attrs,
        "name": obj.name,
    }


def decode_xarray(obj):
    assert obj["_rtype"] == "xarray"
    return xr.DataArray(
        data=obj["data"],
        dims=obj["dims"],
        attrs=obj.get("attrs", {}),
        name=obj.get("name", None),
    )


async def get_server(env_name: str = "default"):
    server = await connect_to_server({"server_url": get_server_url(env_name)})
    server.register_codec({"name": "xarray", "type": xr.DataArray, "encoder": encode_xarray, "decoder": decode_xarray})
    return server
