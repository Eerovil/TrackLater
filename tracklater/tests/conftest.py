
import pytest
import settings
import example_settings


@pytest.fixture(autouse=True)
def mock_jira_settings(monkeypatch):
    for module_setting in [item for item in dir(settings) if not item.startswith("__")]:
        monkeypatch.setattr(
            'settings.{}'.format(module_setting),
            getattr(example_settings, module_setting)
        )
