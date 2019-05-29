from timemodules.toggl import Parser

import pytest
import os

from datetime import datetime, timedelta
from models import Entry

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.utcnow() - timedelta(days=7), datetime.utcnow())
    return _parser


def test_toggl_get_entries(parser):
    """
    """
    data = parser.get_entries()
    assert len(data) == 3


def test_toggl_get_projects(parser):
    """
    """
    data = parser.get_projects()
    assert len(data) == 4
