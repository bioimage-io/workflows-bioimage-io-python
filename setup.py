import json
from pathlib import Path

from setuptools import find_namespace_packages, setup

# Get the long description from the README file
ROOT_DIR = Path(__file__).parent.resolve()
long_description = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
VERSION_FILE = ROOT_DIR / "bioimageio" / "workflows" / "VERSION"
VERSION = json.loads(VERSION_FILE.read_text())["version"]


setup(
    name="bioimageio.workflows",
    version=VERSION,
    description="BioImage.IO Workflows extending the bioimageio.core functionality.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bioimage-io/workflows-bioimage-io-python",
    author="Bioimage Team",
    classifiers=[  # Optional
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    packages=find_namespace_packages(exclude=["tests"]),  # Required
    install_requires=[
        "bioimageio.core==0.5.8.*",
        "imageio>=2.5",
        "numpy",
        "tqdm",
        "xarray",
        "tifffile",
        "dask",
        "typer",
        "imjoy-rpc",
    ],
    include_package_data=True,
    extras_require={
        "test": ["pytest", "pytest-asyncio", "black", "mypy"],
        "dev": ["pre-commit"],
        "pytorch": ["torch>=1.13", "torchvision"],
        "tensorflow1": ["tensorflow==1.*"],
        "tensorflow2": ["tensorflow==2.*"],
        "onnx": ["onnxruntime>=1.12"],
        "stardist_tf1": ["stardist[tf1]", "tensorflow==1.*"],
        "stardist": ["stardist", "tensorflow==2.*"],
    },
    project_urls={  # Optional
        "Bug Reports": "https://github.com/bioimage-io/workflows-bioimage-io-python/issues",
        "Source": "https://github.com/bioimage-io/workflows-bioimage-io-python",
    },
    entry_points={"console_scripts": ["bioimageio = bioimageio.workflows.__main__:app"]},
)
