# How to contribute

* Post an issue about anything
* After creating an issue you can also start to work on your own pull request. This could be a module or general improvements.

# Coding conventions

* Use basic PEP8 style for python.
* Add type hints if you can. If you can't, it's also fine. Mypy and flake8 are used to validate code.

# Getting started with the code

Clone the repo
```
git clone git@github.com:Eerovil/TrackLater.git
cd TrackLater
```
Create a virtualenv (recommended)
```
mkvirtualenv tracklater -p python3.7 -a .
```
Install requirements and launch in debug mode.
```
pip install -r requirements.txt
FLASK_APP=tracklater FLASK_DEBUG=1 python -m flask run
```
