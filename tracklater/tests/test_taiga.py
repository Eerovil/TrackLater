from timemodules.taiga import Parser

import pytest
import os
import pytz
import settings

from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))

HEL = pytz.timezone(settings.TIMEZONE)


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    return _parser


def test_get_issues(parser):
    """
    """
    data = parser.get_issues()
    assert len(data) == 3
