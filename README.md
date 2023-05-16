# Dependencies
Project dependencies are defined in the `requirements.in` file.
Then we use `pip-tools` package to produce a lock-file with pinned package versions for reproducability.

To generate a lock-file from `requirements-in` run:
```shell
pip-compile --resolver=backtracing requirements.in
```
This will generate `requirements.txt` which you then can use during the installationg process.

Dev dependencies are managed similarly, but in `requirements-dev.in` and `requirements-dev.txt` files and should only be installed during development and NOT in production.

# Installation
```shell
git clone <this repo>
cd men_support
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
```
