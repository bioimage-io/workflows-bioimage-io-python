import pytest


@pytest.mark.asyncio
async def test_hello():
    from bioimageio.workflows.envs.default import hello

    assert hello("test") == "test"
