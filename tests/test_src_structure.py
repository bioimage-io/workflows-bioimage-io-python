import re
from pathlib import Path

import pytest

TESTS = Path(__file__).parent
WF = TESTS.parent / "src" / "bioimageio" / "workflows"


imported_envs = {e.strip() for e in (WF / "envs" / "__init__.py").read_text().replace("from . import ", "").split(",")}
remote_template = (WF / "envs" / "default" / "remote.py").read_text()
init_template = (WF / "envs" / "stardist" / "__init__.py").read_text()

test_pattern = r"async def test_(\S+)\(.*\):"


def get_from_imports(code: str):
    return {name.strip() for line in code.strip().split("\n") for name in line.split("import")[1].split(",")}


all_wf_names = get_from_imports((WF / "__init__.py").read_text())


@pytest.mark.parametrize(
    "env_name,env",
    [(env.name, env) for env in (WF / "envs").glob("*") if not env.name.startswith("__")],
)
def test_env_module_structure(env_name, env):
    assert env_name in imported_envs
    assert (env / "local.py").exists()
    init = env / "__init__.py"
    assert init.exists()
    remote = env / "remote.py"
    assert remote.exists()
    init_text = init.read_text()
    if env_name != "default":
        assert init_text == init_template
        assert remote.read_text() == remote_template

    # no public submodules other than local/remote
    for submodule_path in env.glob("*"):
        assert submodule_path.name.startswith("_") or submodule_path.name in ("local.py", "remote.py")

    wf_names = get_from_imports((env / "local.py").read_text())
    missing_top_level_import = wf_names - all_wf_names
    assert not missing_top_level_import, f"Missing import of {missing_top_level_import} in bioimageio/workflows/__init__.py"
    for test_path in TESTS.glob("test_*/test_*.py"):
        for tested in re.findall(test_pattern, test_path.read_text()):
            if tested in wf_names:
                wf_names.remove(tested)

    assert not wf_names, f"no tests found for {wf_names}"


