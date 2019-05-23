from main import Parser

import pytest

from timemodules.interfaces import AbstractProvider

from datetime import datetime, timedelta

from utils import obj_from_dict


@pytest.fixture(autouse=True)
def mock_main(monkeypatch):
    monkeypatch.setattr('settings.ENABLED_MODULES', [
        'jira',
        'gitmodule',
        'slack',
    ])


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    return _parser


def test_parse(parser):
    parser.parse()


def test_obj_from_dict():
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


class TestProvider(AbstractProvider):
    def normal_method(self, arg1=None):
        return "normal"

    def test_normal_method(self, arg1=None):
        return "test"


def test_provider_normal(monkeypatch):
    monkeypatch.setattr('settings.TESTING', False)
    provider = TestProvider()

    assert provider.normal_method() == "normal"


def test_provider_testing(monkeypatch):
    provider = TestProvider()

    assert provider.normal_method() == "test"
