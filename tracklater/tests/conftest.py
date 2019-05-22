
import pytest
import settings
import example_settings
import re


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Replace settings completely with example_settings
    """
    for module_setting in [item for item in dir(settings) if not item.startswith("__")]:
        if module_setting == 'helper':
            continue
        monkeypatch.setattr(
            'settings.{}'.format(module_setting),
            getattr(example_settings, module_setting)
        )

    monkeypatch.setattr('settings.TESTING', True)

    # Test settings for Jira
    monkeypatch.setattr('settings.JIRA', {
        'group1': {
            'CREDENTIALS': ('', ''),
            'URL': 'mock://jira.test',
            'PROJECT_KEY': 'TEST',
        }
    })

    # Test settings for Git
    monkeypatch.setattr('settings.GIT', {
        'global': {
            'EMAILS': ['test.person@email.com'],
        },
        'group1': {
            'REPOS': ['path1', 'path2']
        },
        'group2': {
            'REPOS': ['path3']
        },
    })

    # Test settings for Slack
    monkeypatch.setattr('settings.SLACK', {
        'global': {
            'API_KEY': '',
            'USER_ID': '1',
        }
    })
