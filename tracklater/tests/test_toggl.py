from timemodules.toggl import Parser

import pytest
import os

from datetime import datetime, timedelta
from models import Entry

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
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


def test_toggl_add_modify_delete(parser: Parser):
    parser.entries = parser.get_entries()
    entry = Entry(
        id="4",
        start_time=datetime.now() - timedelta(hours=2),
        end_time=datetime.now() - timedelta(hours=1),
        title="Toggl new entry (4)",
        project="10",
    )
    data = parser.create_entry(entry, None)
    assert len(data) == 1
    assert len(parser.entries) == 4
    assert parser.entries[-1].title == entry.title

    entry.title = "Toggl modified entry"
    parser.update_entry("4", entry, None)
    assert len(parser.entries) == 4
    assert parser.entries[-1].title == entry.title

    parser.delete_entry("4")
    assert len(parser.entries) == 3
