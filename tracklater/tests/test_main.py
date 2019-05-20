from main import Parser

import pytest

from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def mock_main(monkeypatch):
    monkeypatch.setattr('settings.ENABLED_MODULES', [
        'jira',
        'gitmodule',
    ])


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    return _parser


def test_parse(parser):
    parser.parse()


def test_obj_from_dict(obj_from_dict):
    _dict = {
        'test(arg1,arg2)': {
            'foo': {
                'bar': 'The Crazy End'
            }
        },
        'test(arg1)': {
            'foo': {
                'bar': 'The Good End'
            }
        },
        'test()': {
            'foo': {
                'bar': 'The Best End'
            }
        }
    }
    obj = obj_from_dict(_dict)

    assert obj.test('arg1', 'arg2').foo.bar == 'The Crazy End'
    assert obj.test('arg1').foo.bar == 'The Good End'
    assert obj.test().foo.bar == 'The Best End'
