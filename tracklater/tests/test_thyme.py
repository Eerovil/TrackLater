from tracklater.timemodules.thyme import Parser

import pytest
import os
from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.utcnow() - timedelta(days=7), datetime.utcnow())
    return _parser


def test_get_entries(parser):
    """
    """
    data = parser.get_entries()
    assert len(data) == 1
