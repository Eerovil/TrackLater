from tracklater.timemodules.toggl import Parser

import pytest
import os

from datetime import datetime, timedelta
from tracklater.models import Entry

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


def test_toggl_add_modify_delete(parser: Parser):
    parser.entries = parser.get_entries()
    entry = Entry(
        id="4",
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow() - timedelta(hours=1),
        title="Toggl new entry (4)",
        project="10",
    )
    entry = parser.create_entry(entry, None)
    assert entry.id == "4"

    entry.title = "Toggl modified entry"
    entry = parser.update_entry("4", entry, None)
    assert entry.title == "Toggl modified entry"

    parser.delete_entry("4")
