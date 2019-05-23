from timemodules.toggl import Parser

import pytest
import os

from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    return _parser


def test_get_entries(parser):
    """
    """
    data = parser.get_entries()
    assert len(data) == 3
