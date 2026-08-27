import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from tracklater import ai_local_codex as codex


def test_run_codex_uses_sol_structured_ephemeral_exec(monkeypatch):
    captured = {}

    def fake_run(cmd, input, capture_output, text, timeout, cwd):
        captured.update(cmd=cmd, input=input, cwd=cwd, timeout=timeout)
        output_path = cmd[cmd.index('--output-last-message') + 1]
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('{"entries":[]}')
        schema_path = cmd[cmd.index('--output-schema') + 1]
        with open(schema_path, 'r', encoding='utf-8') as f:
            captured['schema'] = json.load(f)
        return SimpleNamespace(returncode=0, stdout='', stderr='')

    monkeypatch.setattr(codex, '_binary', lambda: 'codex')
    monkeypatch.setattr(codex, '_model', lambda: 'gpt-5.6-sol')
    monkeypatch.setattr(codex, '_effort', lambda: 'low')
    monkeypatch.setattr(codex.subprocess, 'run', fake_run)

    assert codex.run_codex('billing prompt', timeout=12) == '{"entries":[]}'
    assert captured['cmd'][:2] == ['codex', 'exec']
    assert captured['cmd'][captured['cmd'].index('--model') + 1] == 'gpt-5.6-sol'
    assert 'model_reasoning_effort="low"' in captured['cmd']
    assert '--ephemeral' in captured['cmd']
    assert '--ignore-user-config' in captured['cmd']
    assert captured['cmd'][captured['cmd'].index('--sandbox') + 1] == 'read-only'
    assert captured['input'] == 'billing prompt'
    assert captured['schema']['type'] == 'object'


@pytest.mark.parametrize(
    'day, expected_hours',
    [('2026-03-29', 23), ('2026-10-25', 25)],
)
def test_single_day_validation_accepts_dst_days(monkeypatch, day, expected_hours):
    from tracklater import settings

    monkeypatch.setattr(settings, 'TIMEZONE', 'Europe/Helsinki', raising=False)
    start, end = codex._local_day_utc_bounds(day)

    assert (end - start) == timedelta(hours=expected_hours)
    assert codex.validate_single_local_day_range(start, end) == day


def test_single_day_validation_rejects_partial_day(monkeypatch):
    from tracklater import settings

    monkeypatch.setattr(settings, 'TIMEZONE', 'Europe/Helsinki', raising=False)
    start, end = codex._local_day_utc_bounds('2026-07-16')

    with pytest.raises(ValueError, match='midnight-to-midnight'):
        codex.validate_single_local_day_range(
            start + timedelta(minutes=30), end,
        )


def _configure_stream(monkeypatch, result):
    from tracklater import settings

    target = '2026-07-16'
    monkeypatch.setattr(settings, 'ENABLED_MODULES', ['gitmodule', 'kimai'])
    monkeypatch.setattr(settings, 'TIMEZONE', 'Europe/Helsinki', raising=False)
    monkeypatch.setattr(codex, '_has_source_data', lambda *_: True)
    monkeypatch.setattr(
        codex, '_allowed_local_projects', lambda *_: {'group1:Development'},
    )
    monkeypatch.setattr(codex, 'gather_signal', lambda *_: {
        '2026-07-15': 'adjacent signal',
        target: 'selected signal',
        '2026-07-17': 'adjacent signal',
    })
    monkeypatch.setattr(codex, 'run_codex', lambda *_: result)
    monkeypatch.setattr(codex, '_write_suggestions', lambda *_args, **_kwargs: None)
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
        codex, 'persist_local_entries',
        lambda entries, start, end, replace_existing: persisted.append(
            (entries, start, end, replace_existing)
        ),
    )
    start, end = codex._local_day_utc_bounds(target)

    events = list(codex.stream_populate_local_entries_ai(
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
        codex, 'persist_local_entries', lambda *_args, **_kwargs: persisted.append(1),
    )
    start, end = codex._local_day_utc_bounds(target)

    events = list(codex.stream_populate_local_entries_ai(
        start, end, replace_existing=True, only_day=target,
    ))

    assert persisted == []
    assert events[0]['type'] == 'day_error'
    assert 'preserved' in events[0]['error']
    assert events[-1]['type'] == 'done'
