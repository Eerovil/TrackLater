"""
AI-backed local billing entries via the `claude` CLI (Opus).

The rule-based path (ai_local.populate_local_entries) is fast and deterministic.
This path hands the same git + ActivityWatch signal, plus ENTRY_GUIDEBOOK.md, to
Claude Opus and asks it to produce billing entries — better judgement on titles,
client selection and billable hours than the hardcoded rules or Gemini.

Config (optional) in ~/.config/tracklater.json:
    "CLAUDE": {"global": {"BIN": "claude", "MODEL": "opus",
                          "EFFORT": "low", "TIMEOUT": 420}}
EFFORT maps to the CLI --effort flag; opus 'low' runs ~2-5x faster than the
default with equivalent output quality on this task.
The container running this must have the `claude` CLI installed and authenticated.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - py<3.9
    ZoneInfo = None  # type: ignore

from tracklater import settings
from tracklater.database import db
from tracklater.models import Entry, EntrySuggestion
from tracklater.ai_local import (
    MODULE_NAME,
    _allowed_local_projects,
    _has_source_data,
    persist_local_entries,
)

import logging
logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
GUIDEBOOK_PATH = os.path.join(REPO_ROOT, 'ENTRY_GUIDEBOOK.md')
# Optional, gitignored: client-specific vocabulary/branch-title tables and examples.
# Appended to the generic guidebook at runtime when present.
GUIDEBOOK_LOCAL_PATH = os.path.join(REPO_ROOT, 'ENTRY_GUIDEBOOK.local.md')
DEFAULT_MODEL = 'opus'
DEFAULT_TIMEOUT = 420  # per single-day claude call
DEFAULT_EFFORT = 'low'  # opus 'low' is ~2-5x faster with equivalent quality here


# --------------------------------------------------------------------------- #
# Config helpers
# --------------------------------------------------------------------------- #
def _claude_cfg() -> Dict[str, Any]:
    cfg = getattr(settings, 'CLAUDE', None) or {}
    return cfg.get('global', {}) if isinstance(cfg, dict) else {}


def _binary() -> str:
    return _claude_cfg().get('BIN') or shutil.which('claude') or 'claude'


def _model() -> str:
    return _claude_cfg().get('MODEL') or DEFAULT_MODEL


def _timeout() -> int:
    return int(_claude_cfg().get('TIMEOUT') or DEFAULT_TIMEOUT)


def _effort() -> str:
    return _claude_cfg().get('EFFORT') or DEFAULT_EFFORT


def _tz():
    name = getattr(settings, 'TIMEZONE', None) or 'Europe/Helsinki'
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo('Europe/Helsinki')


def _to_local(dt: datetime) -> datetime:
    """Naive UTC datetime (how source modules store time) -> naive local."""
    tz = _tz()
    if tz is None or ZoneInfo is None:
        return dt + timedelta(hours=3)  # EEST fallback
    return dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(tz).replace(tzinfo=None)


def _to_utc(dt: datetime) -> datetime:
    """Naive local datetime (what the model emits) -> naive UTC, how every other
    module stores time. The frontend stamps stored times as UTC for display, so
    local entries MUST be persisted in UTC or they render/export hours off."""
    tz = _tz()
    if tz is None or ZoneInfo is None:
        return dt - timedelta(hours=3)  # EEST fallback
    return dt.replace(tzinfo=tz).astimezone(ZoneInfo('UTC')).replace(tzinfo=None)


# --------------------------------------------------------------------------- #
# Signal gathering (git commits + bridged ActivityWatch sessions)
# --------------------------------------------------------------------------- #
_BRANCH_RE = re.compile(r'\[([^\]]+)\]')


def _branch_slug(text: str) -> str:
    m = _BRANCH_RE.search(text or '')
    if not m:
        return ''
    slug = m.group(1).split('/')[-1]
    return '' if slug.lower() in ('undefined', 'master', 'main', 'origin', 'head') else slug


def _bridge(sessions: List[tuple], gap=timedelta(minutes=15)) -> List[tuple]:
    """Merge (start,end) pairs whose gap <= gap; bridged gaps count as work."""
    if not sessions:
        return []
    sessions = sorted(sessions)
    out = [list(sessions[0])]
    for s, e in sessions[1:]:
        if s - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def gather_signal(start_date: datetime, end_date: datetime) -> Dict[str, str]:
    """Per-LOCAL-day text digest of git + bridged AW activity.

    Returns {`YYYY-MM-DD`: digest}. We widen the query window so a local day's
    late-evening / early-morning activity (which lands on an adjacent UTC date)
    is still bucketed onto the right local day before slicing.
    """
    win_start = start_date - timedelta(hours=12)
    win_end = end_date + timedelta(hours=12)
    git_rows = Entry.query.filter(
        Entry.module == 'gitmodule',
        Entry.start_time >= win_start,
        Entry.start_time <= win_end,
    ).order_by(Entry.start_time).all()
    aw_rows = Entry.query.filter(
        Entry.module == 'activitywatch',
        Entry.start_time >= win_start,
        Entry.start_time <= win_end,
    ).order_by(Entry.start_time).all()

    by_day_commits: Dict[str, list] = defaultdict(list)
    for row in git_rows:
        local = _to_local(row.start_time)
        msg = (row.text or row.title or '').split('\n')[0]
        # strip "<group> [branch] - " prefix to get the message
        msg_clean = re.sub(r'^\S+\s+\[[^\]]*\]\s*-\s*', '', msg)
        by_day_commits[local.strftime('%Y-%m-%d')].append(
            (local, row.group or '?', _branch_slug(msg), msg_clean[:80])
        )

    by_day_aw: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for row in aw_rows:
        if not row.end_time or not row.group:
            continue
        ls, le = _to_local(row.start_time), _to_local(row.end_time)
        by_day_aw[ls.strftime('%Y-%m-%d')][row.group].append((ls, le))

    lo, hi = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    days = sorted(d for d in (set(by_day_commits) | set(by_day_aw)) if lo <= d <= hi)
    digests: Dict[str, str] = {}
    for day in days:
        dow = datetime.strptime(day, '%Y-%m-%d').strftime('%a')
        lines = [f'## {day} ({dow})']
        aw = by_day_aw.get(day, {})
        if aw:
            lines.append('  ActivityWatch (bridged 15min, grouped):')
            for group, sessions in sorted(aw.items()):
                merged = _bridge(sessions)
                hours = sum((e - s).total_seconds() for s, e in merged) / 3600
                spans = ', '.join(f'{s.strftime("%H:%M")}-{e.strftime("%H:%M")}' for s, e in merged)
                lines.append(f'    {group}: {hours:.1f}h  [{spans}]')
        commits = by_day_commits.get(day, [])
        if commits:
            lines.append(f'  Git commits ({len(commits)}):')
            for local, group, branch, msg in commits:
                br = f' ({branch})' if branch else ''
                lines.append(f'    {local.strftime("%H:%M")} {group}{br}: {msg}')
        digests[day] = '\n'.join(lines)
    return digests


# --------------------------------------------------------------------------- #
# Prompt + CLI
# --------------------------------------------------------------------------- #
def _read_guidebook() -> str:
    parts: List[str] = []
    try:
        with open(GUIDEBOOK_PATH, 'r', encoding='utf-8') as f:
            parts.append(f.read())
    except OSError:
        logger.warning("ENTRY_GUIDEBOOK.md not found at %s", GUIDEBOOK_PATH)
    if os.path.exists(GUIDEBOOK_LOCAL_PATH):
        try:
            with open(GUIDEBOOK_LOCAL_PATH, 'r', encoding='utf-8') as f:
                parts.append(
                    '\n\n================ LOCAL CLIENT SPECIFICS ================\n'
                    + f.read()
                )
        except OSError:
            pass
    return '\n'.join(parts) if parts else '(guidebook unavailable)'


def build_day_prompt(
    day: str, day_signal: str, allowed_projects: set, prior_titles: List[str],
) -> str:
    """Prompt Claude for a SINGLE day's entries. Small prompts keep each call
    fast and well under the CLI timeout, and isolate failures to one day."""
    guidebook = _read_guidebook()
    projects = '\n'.join(f'  - {p}' for p in sorted(allowed_projects))
    carry = (
        '\nEpic titles already used earlier this week (reuse the matching one to '
        'carry an epic forward, per the guidebook):\n  '
        + '\n  '.join(prior_titles)
        if prior_titles else ''
    )
    return f"""You reconstruct manual billing time entries from git + ActivityWatch data.
Follow the guidebook below EXACTLY — it encodes the user's real billing behaviour.

================ GUIDEBOOK ================
{guidebook}
================ END GUIDEBOOK ================

Allowed projects (use these exact `group:Project` strings, nothing else):
{projects}
{carry}

Source signal for {day} ONLY (LOCAL time already):
{day_signal}

TASK: produce the billing entries for {day} by applying every rule in the
guidebook — sub-project folding, client selection thresholds, branch-slug titles,
bridged billable hours with the weekday-daytime / evening / weekend rules, and
blocks snapped to :00/:30.

For EACH entry also provide ranked alternatives the user might pick instead when
editing: `project_options` (2-4 plausible `group:Project` for this block, BEST
first — the first MUST equal `project`) and `title_options` (2-4 plausible titles,
BEST first — the first MUST equal `title`). These are hints for a dropdown.

Output ONLY a JSON array, no prose, no code fence. Each item:
{{"date":"{day}","start":"HH:MM","end":"HH:MM","project":"group:Project","title":"...",
  "project_options":["group:Project", ...],"title_options":["...", ...]}}
Times are LOCAL 24h. Entries must not overlap. If the day is unbillable (leave /
no work), output an empty array []."""


def run_claude(prompt: str, timeout: Optional[int] = None) -> str:
    """Invoke the claude CLI headlessly and return the model's text result."""
    cmd = [
        _binary(), '-p', prompt,
        '--model', _model(),
        '--effort', _effort(),
        '--output-format', 'json',
    ]
    # Run in an isolated cwd so the CLI doesn't load this repo's project context.
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout or _timeout(), cwd=tmp,
            )
        except FileNotFoundError:
            raise ValueError(
                "`claude` CLI not found. Install it in this environment or set "
                "CLAUDE.global.BIN in settings."
            )
        except subprocess.TimeoutExpired:
            raise ValueError("claude CLI timed out")
    if proc.returncode != 0:
        raise ValueError(
            "claude CLI failed (exit {}): {}".format(
                proc.returncode, (proc.stderr or proc.stdout or '')[:500]
            )
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise ValueError("claude CLI returned non-JSON envelope: " + proc.stdout[:300])
    if payload.get('is_error'):
        raise ValueError("claude reported an error: " + str(payload.get('result'))[:300])
    return payload.get('result', '')


def parse_entries(
    result_text: str, allowed_projects: set,
) -> List[Dict[str, Any]]:
    """Parse the model's JSON array into entry dicts with naive-local datetimes."""
    text = result_text.strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text).strip()
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1:
        raise ValueError("No JSON array in claude output: " + text[:200])
    items = json.loads(text[start:end + 1])

    entries: List[Dict[str, Any]] = []
    for item in items:
        project = item['project']
        if project not in allowed_projects:
            logger.warning("Skipping entry with unknown project %r", project)
            continue
        day = item['date']
        s = datetime.strptime(f"{day} {item['start']}", '%Y-%m-%d %H:%M')
        e = datetime.strptime(f"{day} {item['end']}", '%Y-%m-%d %H:%M')
        if e <= s:
            e += timedelta(days=1)  # crossed midnight
        # Model reasons in local time; persist UTC to match every other module.
        s, e = _to_utc(s), _to_utc(e)
        title = str(item.get('title') or 'Work')[:255]
        # Ranked editor hints: keep only allowed projects, ensure the chosen one
        # leads, dedupe, cap at 4. Fall back to the single chosen value.
        popts = [p for p in (item.get('project_options') or []) if p in allowed_projects]
        popts = [project] + [p for p in popts if p != project]
        topts = [str(t)[:255] for t in (item.get('title_options') or []) if t]
        topts = [title] + [t for t in topts if t != title]
        entries.append({
            'start_time': s,
            'end_time': e,
            'title': title,
            'project': project,
            'project_options': list(dict.fromkeys(popts))[:4],
            'title_options': list(dict.fromkeys(topts))[:4],
        })
    entries.sort(key=lambda x: x['start_time'])
    return entries


def _write_suggestions(
    entries_data: List[Dict[str, Any]],
    win_start: Optional[datetime] = None,
    win_end: Optional[datetime] = None,
    replace: bool = True,
) -> None:
    """Persist per-entry project/title hints (EntrySuggestion rows). When replace
    and a window is given, clear existing hints starting in [win_start, win_end]
    first so a re-fill doesn't accumulate stale rows.

    Best-effort: suggestions are a convenience layer, so a failure here must never
    break the (already-committed) entry persistence — log and move on."""
    try:
        if replace and win_start is not None and win_end is not None:
            EntrySuggestion.query.filter(
                EntrySuggestion.start_time >= win_start,
                EntrySuggestion.start_time <= win_end,
            ).delete()
        for item in entries_data:
            db.session.add(EntrySuggestion(
                start_time=item['start_time'],
                end_time=item['end_time'],
                date_group=item['start_time'].strftime('%Y-%m-%d'),
                projects=item.get('project_options') or [item['project']],
                titles=item.get('title_options') or [item['title']],
            ))
        db.session.commit()
    except Exception:  # noqa: BLE001 - hints are non-critical
        logger.exception("Failed to write entry suggestions (ignored)")
        db.session.rollback()


def populate_local_entries_ai(
    start_date: datetime,
    end_date: datetime,
    replace_existing: bool = True,
) -> List[Entry]:
    """Create local entries by asking Claude Opus, then persist them."""
    if MODULE_NAME not in settings.ENABLED_MODULES:
        raise ValueError("local module is not enabled")
    if not _has_source_data(start_date, end_date):
        raise ValueError(
            "No source timemodule entries in this range. Fetch activitywatch/git/etc. first."
        )
    allowed_projects = _allowed_local_projects(start_date, end_date)
    if not allowed_projects:
        raise ValueError("No LOCAL projects configured")

    digests = gather_signal(start_date, end_date)
    if not digests:
        raise ValueError(
            "No git/ActivityWatch signal in this range to reconstruct from."
        )

    # One claude call per day: small prompts stay under the CLI timeout and a
    # slow/failed day can't sink the whole week. Titles carry forward across days.
    entries_data: List[Dict[str, Any]] = []
    prior_titles: List[str] = []
    errors: List[str] = []
    for day in sorted(digests):
        prompt = build_day_prompt(day, digests[day], allowed_projects, prior_titles)
        logger.info("Calling claude (%s) for local entries %s", _model(), day)
        try:
            raw = run_claude(prompt)
            day_entries = parse_entries(raw, allowed_projects)
        except ValueError as exc:
            logger.warning("claude failed for %s: %s", day, exc)
            errors.append(f"{day}: {exc}")
            continue
        entries_data.extend(day_entries)
        for e in day_entries:
            if e['title'] not in prior_titles:
                prior_titles.append(e['title'])

    if not entries_data:
        raise ValueError(
            "claude produced no entries"
            + (" (" + "; ".join(errors) + ")" if errors else "")
        )
    if errors:
        logger.warning("Some days failed and were skipped: %s", "; ".join(errors))
    created = persist_local_entries(
        entries_data, start_date, end_date, replace_existing=replace_existing,
    )
    _write_suggestions(entries_data, start_date, end_date, replace=replace_existing)
    return created


# --------------------------------------------------------------------------- #
# Feature 2: streaming week-fill (per-day, cancellable, keeps finished days)
# --------------------------------------------------------------------------- #
def _local_day_utc_bounds(day: str) -> (datetime, datetime):
    """UTC [start, end) covering one LOCAL calendar day, for scoping the
    per-day draft-delete in persist_local_entries to just that day."""
    local_start = datetime.strptime(day, '%Y-%m-%d')
    local_end = local_start + timedelta(days=1)
    return _to_utc(local_start), _to_utc(local_end)


def stream_populate_local_entries_ai(
    start_date: datetime,
    end_date: datetime,
    replace_existing: bool = True,
):
    """Generator variant of populate_local_entries_ai for streaming.

    Yields progress dicts as each day completes and persists that day's entries
    immediately (per-day), so a cancellation (the consumer stops iterating) keeps
    the days already finished and leaves untouched days alone. Each yielded dict:
        {'type': 'progress', 'day', 'done', 'total', 'count'}
        {'type': 'day_error', 'day', 'error'}
        {'type': 'done', 'count', 'errors'}
        {'type': 'error', 'error'}   (fatal, before any day ran)
    """
    if MODULE_NAME not in settings.ENABLED_MODULES:
        yield {'type': 'error', 'error': 'local module is not enabled'}
        return
    if not _has_source_data(start_date, end_date):
        yield {'type': 'error', 'error':
               'No source timemodule entries in this range. '
               'Fetch activitywatch/git/etc. first.'}
        return
    allowed_projects = _allowed_local_projects(start_date, end_date)
    if not allowed_projects:
        yield {'type': 'error', 'error': 'No LOCAL projects configured'}
        return
    digests = gather_signal(start_date, end_date)
    if not digests:
        yield {'type': 'error', 'error':
               'No git/ActivityWatch signal in this range to reconstruct from.'}
        return

    days = sorted(digests)
    total = len(days)
    prior_titles: List[str] = []
    errors: List[str] = []
    total_count = 0
    for idx, day in enumerate(days):
        prompt = build_day_prompt(day, digests[day], allowed_projects, prior_titles)
        logger.info("Streaming claude (%s) for local entries %s", _model(), day)
        try:
            raw = run_claude(prompt)
            day_entries = parse_entries(raw, allowed_projects)
        except ValueError as exc:
            logger.warning("claude failed for %s: %s", day, exc)
            errors.append(f"{day}: {exc}")
            yield {'type': 'day_error', 'day': day, 'error': str(exc)}
            continue
        # Persist THIS day now, scoping the draft-delete to the local day so a
        # later cancel can't roll it back and untouched days keep their entries.
        d_start, d_end = _local_day_utc_bounds(day)
        try:
            if day_entries:
                persist_local_entries(
                    day_entries, d_start, d_end, replace_existing=replace_existing,
                )
                _write_suggestions(day_entries, d_start, d_end, replace=replace_existing)
            total_count += len(day_entries)
        except ValueError as exc:
            logger.warning("persist failed for %s: %s", day, exc)
            errors.append(f"{day}: {exc}")
            yield {'type': 'day_error', 'day': day, 'error': str(exc)}
            continue
        for e in day_entries:
            if e['title'] not in prior_titles:
                prior_titles.append(e['title'])
        yield {'type': 'progress', 'day': day, 'done': idx + 1,
               'total': total, 'count': len(day_entries)}
    yield {'type': 'done', 'count': total_count, 'errors': errors}


# --------------------------------------------------------------------------- #
# Feature 1: single entry from a double-click (grow a block from the click seed)
# --------------------------------------------------------------------------- #
def build_click_prompt(
    day: str, day_signal: str, allowed_projects: set, prior_titles: List[str],
    click_local: datetime, gap_lo_local: Optional[datetime],
    gap_hi_local: Optional[datetime],
) -> str:
    """Prompt Claude for ONE entry grown outward from the click point."""
    guidebook = _read_guidebook()
    projects = '\n'.join(f'  - {p}' for p in sorted(allowed_projects))
    carry = (
        '\nEpic titles already in use this week (reuse the matching one to carry an '
        'epic forward, per the guidebook):\n  ' + '\n  '.join(prior_titles)
        if prior_titles else ''
    )
    bounds = ''
    if gap_lo_local is not None:
        bounds += f"\n- The entry MUST NOT start before {gap_lo_local.strftime('%H:%M')} (previous entry)."
    if gap_hi_local is not None:
        bounds += f"\n- The entry MUST NOT end after {gap_hi_local.strftime('%H:%M')} (next entry)."
    return f"""You reconstruct ONE manual billing time entry from git + ActivityWatch data.
Follow the guidebook below EXACTLY for client/project selection, titles and the
billable-hours model.

================ GUIDEBOOK ================
{guidebook}
================ END GUIDEBOOK ================

Allowed projects (use these exact `group:Project` strings, nothing else):
{projects}
{carry}

Source signal for {day} (LOCAL time already):
{day_signal}

TASK: the user double-clicked the timeline at {click_local.strftime('%H:%M')} to create
a SINGLE entry there. Build exactly ONE entry:
1. SEED: within ±30 min of {click_local.strftime('%H:%M')}, find the single dominant
   project/component (its commits + ActivityWatch activity). That is this entry's
   project. Fold sub-projects into their parent per the guidebook.
2. GROW: extend the block earlier and later from the click. Keep extending each side
   while the SAME project/component's commits/activity continue. STOP a side as soon
   as the focus clearly switches to a different project/component, or at a real AFK
   gap.{bounds}
3. Snap start/end to :00/:30. Title per the guidebook (branch slug first).
4. If there is NO meaningful signal within ±30 min of the click, output an empty
   array [] (the UI will create a blank entry to fill in by hand).

Also provide ranked alternatives for the editor dropdown: `project_options` (2-4
plausible `group:Project`, BEST first — first MUST equal `project`) and
`title_options` (2-4 plausible titles, BEST first — first MUST equal `title`).

Output ONLY a JSON array with AT MOST ONE item, no prose, no code fence:
[{{"date":"{day}","start":"HH:MM","end":"HH:MM","project":"group:Project","title":"...",
  "project_options":["group:Project", ...],"title_options":["...", ...]}}]
Times are LOCAL 24h."""


def populate_entry_at(
    click: datetime,
    prev_end: Optional[datetime] = None,
    next_start: Optional[datetime] = None,
) -> List[Entry]:
    """Create a single local entry grown from a double-click at `click` (naive UTC).

    `prev_end`/`next_start` (naive UTC) bound the free gap so the result can't
    overlap neighbours. Returns the created entries (0 or 1); an empty list means
    'no signal near the click' — the caller drops a blank manual entry instead.
    """
    if MODULE_NAME not in settings.ENABLED_MODULES:
        raise ValueError("local module is not enabled")
    click_local = _to_local(click)
    day = click_local.strftime('%Y-%m-%d')
    day_start = datetime.strptime(day, '%Y-%m-%d')
    day_end = day_start + timedelta(days=1)
    # gather_signal labels days by the LOCAL date of its bounds, so pass the naive
    # local day window (its ±12h widening still covers the UTC source rows).
    digests = gather_signal(day_start, day_end - timedelta(seconds=1))
    if day not in digests:
        return []  # no signal that day at all -> blank manual entry
    allowed_projects = _allowed_local_projects(_to_utc(day_start), _to_utc(day_end))
    if not allowed_projects:
        raise ValueError("No LOCAL projects configured")
    prompt = build_click_prompt(
        day, digests[day], allowed_projects, [], click_local,
        _to_local(prev_end) if prev_end else None,
        _to_local(next_start) if next_start else None,
    )
    logger.info("Calling claude (%s) for click entry at %s", _model(), click_local)
    raw = run_claude(prompt)
    entries_data = parse_entries(raw, allowed_projects)
    if not entries_data:
        return []
    entries_data = entries_data[:1]  # exactly one entry from a click
    # Hard clamp to the free gap so a stray model end can never overlap neighbours.
    e = entries_data[0]
    if prev_end is not None and e['start_time'] < prev_end:
        e['start_time'] = prev_end
    if next_start is not None and e['end_time'] > next_start:
        e['end_time'] = next_start
    if e['end_time'] <= e['start_time']:
        return []
    created = persist_local_entries(
        entries_data, e['start_time'], e['end_time'], replace_existing=False,
    )
    _write_suggestions(entries_data, e['start_time'], e['end_time'], replace=True)
    return created
