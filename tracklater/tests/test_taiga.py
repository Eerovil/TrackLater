from tracklater.timemodules.taiga import Parser

import pytest
import os

from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.utcnow() - timedelta(days=7), datetime.utcnow())
    return _parser


def test_get_issues(parser):
    """
    """
    data = parser.get_issues()
    assert len(data) == 3
