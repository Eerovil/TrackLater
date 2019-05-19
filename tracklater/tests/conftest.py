
import pytest
import settings
import example_settings


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

    # Test settings for Jira
    monkeypatch.setattr('settings.JIRA', {
        'group1': {
            'CREDENTIALS': ('', ''),
            'URL': 'mock://jira.test',
            'PROJECT_KEY': 'TEST',
        }
    })
