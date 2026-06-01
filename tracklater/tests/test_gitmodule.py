from tracklater.timemodules.gitmodule import Parser

import pytest
import os
from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(autouse=True)
def mock_git(monkeypatch):
    monkeypatch.setattr('tracklater.timemodules.gitmodule.git_time_to_datetime',
                        lambda x: datetime.utcnow() - timedelta(days=4))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.utcnow() - timedelta(days=7), datetime.utcnow())
    _parser.credentials = ('', '')
    return _parser


def test_get_entries(parser):
    data = parser.get_entries()
    assert len(data) == 24
    assert data[0].title == ''


def test_get_entries_hover_text_only(parser):
    data = parser.get_entries()
    assert data[0].text.startswith('path1 [branch1] - ')
    assert 'src/main.py' in data[0].text
    assert 'README.md' in data[0].text
