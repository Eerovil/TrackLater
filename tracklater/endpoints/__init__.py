
from flask import Blueprint

endpoints = Blueprint('endpoints', __name__)

from . import routes  # noqa
