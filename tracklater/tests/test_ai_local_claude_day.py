import json
from datetime import datetime, timedelta

import pytest

from tracklater import ai_local_claude as claude


@pytest.mark.parametrize(
    'day, expected_hours',
    [('2026-03-29', 23), ('2026-10-25', 25)],
)
def test_single_day_validation_accepts_dst_days(monkeypatch, day, expected_hours):
    from tracklater import settings

    monkeypatch.setattr(settings, 'TIMEZONE', 'Europe/Helsinki', raising=False)
    start, end = claude._local_day_utc_bounds(day)

    assert (end - start) == timedelta(hours=expected_hours)
    assert claude.validate_single_local_day_range(start, end) == day


def test_single_day_validation_rejects_partial_day(monkeypatch):
    from tracklater import settings

    monkeypatch.setattr(settings, 'TIMEZONE', 'Europe/Helsinki', raising=False)
    start, end = claude._local_day_utc_bounds('2026-07-16')

    with pytest.raises(ValueError, match='midnight-to-midnight'):
        claude.validate_single_local_day_range(
            start + timedelta(minutes=30), end,
        )


def _configure_stream(monkeypatch, result):
    from tracklater import settings

    target = '2026-07-16'
    monkeypatch.setattr(settings, 'ENABLED_MODULES', ['gitmodule', 'toggl'])
    monkeypatch.setattr(settings, 'TIMEZONE', 'Europe/Helsinki', raising=False)
    monkeypatch.setattr(claude, '_has_source_data', lambda *_: True)
    monkeypatch.setattr(
        claude, '_allowed_local_projects', lambda *_: {'group1:Development'},
    )
    monkeypatch.setattr(claude, 'gather_signal', lambda *_: {
        '2026-07-15': 'adjacent signal',
        target: 'selected signal',
        '2026-07-17': 'adjacent signal',
    })
    monkeypatch.setattr(claude, 'run_claude', lambda *_: result)
    monkeypatch.setattr(claude, '_write_suggestions', lambda *_args, **_kwargs: None)
    return target


def test_single_day_stream_pins_prompt_and_persistence(monkeypatch):
    target = '2026-07-16'
    result = json.dumps([{
        'date': target,
        'start': '09:00',
        'end': '10:00',
        'project': 'group1:Development',
        'title': 'Selected work',
    }])
    target = _configure_stream(monkeypatch, result)
    persisted = []
    monkeypatch.setattr(
        claude, 'persist_local_entries',
        lambda entries, start, end, replace_existing: persisted.append(
            (entries, start, end, replace_existing)
        ),
    )
    start, end = claude._local_day_utc_bounds(target)

    events = list(claude.stream_populate_local_entries_ai(
        start, end, replace_existing=True, only_day=target,
    ))

    assert [event['type'] for event in events] == ['progress', 'done']
    assert events[0]['day'] == target
    assert len(persisted) == 1
    assert persisted[0][1:3] == (start, end)
    assert persisted[0][3] is True


def test_empty_single_day_result_preserves_existing_entries(monkeypatch):
    target = _configure_stream(monkeypatch, '[]')
    persisted = []
    monkeypatch.setattr(
        claude, 'persist_local_entries', lambda *_args, **_kwargs: persisted.append(1),
    )
    start, end = claude._local_day_utc_bounds(target)

    events = list(claude.stream_populate_local_entries_ai(
        start, end, replace_existing=True, only_day=target,
    ))

    assert persisted == []
    assert events[0]['type'] == 'day_error'
    assert 'preserved' in events[0]['error']
    assert events[-1]['type'] == 'done'
