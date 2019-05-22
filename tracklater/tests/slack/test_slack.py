from timemodules.slack import Parser

import pytest
import json
import os
import pytz

from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))

HEL = pytz.timezone('Europe/Helsinki')


@pytest.fixture(autouse=True)
def mock_slack(monkeypatch):
    def _api_call(*args, **kwargs):
        if args[0] == "users.list":
            return {
                "members": [
                    {
                        "id": "1",
                        "profile": {
                            "first_name": "Firstname",
                            "last_name": "Lastename"
                        }
                    },
                    {
                        "id": "2",
                        "profile": {
                            "first_name": "Secondname",
                            "last_name": "Lastename"
                        }
                    }
                ]
            }
        if args[0] == "conversations.list":
            return {"channels": [{"id": "1"}]}
        if args[0] == "conversations.history":
            return {
                "messages": [
                    {
                        "user": "1",
                        "text": "First Message",
                        "ts": "1234567"
                    },
                    {
                        "user": "1",
                        "text": "Second Message",
                        "ts": "1234567"
                    },
                    {
                        "user": "2",
                        "text": "Third Message",
                        "ts": "1234567"
                    }
                ]
            }

    class MockClient(object):
        def __init__(self, *args):
            pass

        def api_call(self, *args, **kwargs):
            return _api_call(*args, **kwargs)

    monkeypatch.setattr('timemodules.slack.WebClient',
                        MockClient)


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    return _parser


def test_get_entries(parser):
    """
    """
    data = parser.get_entries()
    assert len(data) == 2
