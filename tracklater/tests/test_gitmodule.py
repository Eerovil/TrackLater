from tracklater.timemodules.gitmodule import Parser

import pytest
import os
from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(autouse=True)
def mock_git(monkeypatch):
    monkeypatch.setattr('tracklater.timemodules.gitmodule.timestamp_to_datetime',
                        lambda x: datetime.utcnow() - timedelta(days=4))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.utcnow() - timedelta(days=7), datetime.utcnow())
    _parser.credentials = ('', '')
    return _parser


def test_get_entries(parser):
    """
    No real tests for gitmodule... yet.
    """
    data = parser.get_entries()
    assert len(data) == 8
