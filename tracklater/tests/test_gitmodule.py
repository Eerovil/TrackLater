from timemodules.gitmodule import Parser

import pytest
import os
import pytz
import settings

from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))

HEL = pytz.timezone(settings.TIMEZONE)


@pytest.fixture(autouse=True)
def mock_git(monkeypatch):
    monkeypatch.setattr('timemodules.gitmodule.timestamp_to_datetime',
                        lambda x: datetime.now(HEL) - timedelta(days=4))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    _parser.credentials = ('', '')
    return _parser


def test_get_entries(parser):
    """
    No real tests for gitmodule... yet.
    """
    data = parser.get_entries()
    assert len(data) == 8
