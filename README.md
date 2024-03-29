![License](https://img.shields.io/github/license/bioimage-io/workflows-bioimage-io.svg)
![PyPI](https://img.shields.io/pypi/v/bioimageio-workflows.svg?style=popout)
![conda-version](https://anaconda.org/conda-forge/bioimageio.workflows/badges/version.svg)
# BioImage.IO Workflows

This repository contains [workflow implementations](#Workflow-Implementations) and their high level descriptions in the form of [workflow RDFs](#Workflow-Resource-Description-File-(workflow-RDF)).

## Workflow Implementations


## Workflow RDF

A BioImage.IO-compatible workflow Resource Description File (RDF) is a YAML file with a set of specifically defined fields. 

You can find detailed field definitions here: 
   - [workflow RDF spec (latest)](https://github.com/bioimage-io/spec-bioimage-io/blob/gh-pages/workflow_spec_latest.md)
   - [workflow RDF spec (0.2.x)](https://github.com/bioimage-io/spec-bioimage-io/blob/gh-pages/workflow_spec_0_2.md)

The specifications are also available as json schemas: 
   - [workflow RDF spec (0.2.x, json schema)](https://github.com/bioimage-io/spec-bioimage-io/blob/gh-pages/workflow_spec_0_2.json)


# bioimageio command-line interface (CLI) 
The BioImage.IO command line tool makes it easy to work with BioImage.IO RDFs. 
The `bioimageio` command of the [bioimageio.core](https://github.com/bioimage-io/core-bioimage-io-python) package is further extended by this repository's `bioimageio.workflows` package:
type
```
$ bioimageio run-workflow --help
```


## installation
bioimageio.workflows can be installed with either `pip` or `conda` (recommended):

```
# pip
pip install -U bioimageio.workflows

# conda
conda install -c conda-forge bioimageio.workflows
```


## Usage
### Example
in development
start server:
```
python -m bioimageio.workflows.server start-server
```

start a submodule:
```
python -m bioimageio.workflows.server start-submodule-service stardist
```

## Relevant BioImage.IO Environment Variables

For boolean environment variables possible, are case-insensitive, positive values are: "true", "yes", "1".
Any other value is interpreted as "false".

| Name                                  | Default                     | Description                                                                                                                                                                    | defined in           |
|---------------------------------------|-----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| BIOIMAGEIO_SERVER_URL                 | "http://127.0.0.1:9527"     | Use to overwrite the default server address.                                                                                                                                   | bioimageio.workflows |
| BIOIMAGEIO_SERVER_\<env name\>_URL    | \<BIOIMAGEIO_SERVER_URL\>   | Workflow/conda environment specific server url, e.g. 'BIOIMAGEIO_SERVER_STARDIST_URL'.                                                                                         | bioimageio.workflows |
| BIOIMAGEIO_USE_REMOTE_DEFAULT_ENV     | "false"                     | If "true" bioimageio.workflows will execute any workflow defined in the default environment remotely via the hypha server and not locally.                                     | bioimageio.workflows | 
| BIOIMAGEIO_AUTOSTART_SERVER           | "true"                      | If "true" a hypha server will be launched automatically if connecting to a local server url (http://localhost:...) fails.                                                      | bioimageio.workflows | 
| BIOIMAGE_SERVER_CONDA_ENV             | "bioimageio_wf_env_default" | Conda environment to start server in. Only applies if 'BIOIMAGEIO_AUTOSTART_SERVER' is "true".                                                                                 | bioimageio.workflows |
| BIOIMAGEIO_AUTOSTART_ENV_SERVICES     | "true"                      | If "true" the required submodule service is started automatically when required for the first time. Conda environment names follow the pattern 'bioimageio_wf_env_<env-name>'. | bioimageio.workflows |   
| BIOIMAGEIO_AUTOINSTALL_SUBMODULE_ENVS | "true"                      | If "true" missing mamba environments are installed if necessary. Only applies if 'BIOIMAGEIO_AUTOSTART_ENV_SERVICES' is "true".                                                | bioimageio.workflows |
| BIOIMAGEIO_USE_CACHE                  | "true"                      | Enables simple URL to file cache.                                                                                                                                              | bioimageio.spec      |
| BIOIMAGEIO_CACHE_PATH                 | generated tmp folder        | File path for simple URL to file cache; changes of URL source are not detected.                                                                                                | bioimageio.spec      |
| BIOIMAGEIO_CACHE_WARNINGS_LIMIT       | "3"                         | Maximum number of warnings generated for simple cache hits.                                                                                                                    | bioimageio.spec      |

## Changelog
#### bioimageio.workflows tbd
