"""
Build local billing entries from git commits and ActivityWatch (no external AI).
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List

from tracklater import settings
from tracklater.database import db
from tracklater.models import Entry
from tracklater.timemodules.toggl import MODULE_NAME, Parser, resolve_entry_group_project
from tracklater.work_inference import (
    MIN_LOCAL_ENTRY_DURATION,
    MAX_LOCAL_ENTRY_DURATION,
    build_entries_from_commits,
)

import logging
logger = logging.getLogger(__name__)


def _has_source_data(start_date: datetime, end_date: datetime) -> bool:
    source_modules = [m for m in settings.ENABLED_MODULES if m != MODULE_NAME]
    for module in source_modules:
        if Entry.query.filter(
            Entry.module == module,
            Entry.start_time >= start_date,
            Entry.start_time <= end_date,
        ).first():
            return True
    return False


def _allowed_local_projects(start_date: datetime, end_date: datetime) -> set:
    parser = Parser(start_date, end_date)
    return {p.pid for p in parser.get_projects()}


def persist_local_entries(
    entries_data: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
    replace_existing: bool = True,
) -> List[Entry]:
    """
    Validate a list of entry dicts and persist them as ``local`` module entries.

    Each dict needs ``start_time``/``end_time`` (datetime), ``title``, ``project``.
    Shared by the rule-based and AI-backed populate paths.
    """
    for item in entries_data:
        span = item['end_time'] - item['start_time']
        if span > MAX_LOCAL_ENTRY_DURATION:
            raise ValueError(
                "Entry {}–{} exceeds {} hour limit".format(
                    item['start_time'], item['end_time'],
                    MAX_LOCAL_ENTRY_DURATION.total_seconds() / 3600,
                )
            )
        if span < MIN_LOCAL_ENTRY_DURATION:
            raise ValueError(
                "Entry {}–{} is shorter than {} minutes".format(
                    item['start_time'], item['end_time'],
                    MIN_LOCAL_ENTRY_DURATION.total_seconds() / 60,
                )
            )
    if not entries_data:
        raise ValueError(
            "No local entries could be inferred (need git commits or long ActivityWatch sessions)."
        )

    if replace_existing:
        # Only clear unsynced drafts; never wipe entries already pushed to Toggl.
        Entry.query.filter(
            Entry.module == MODULE_NAME,
            Entry.is_draft == True,  # noqa: E712
            Entry.start_time >= start_date,
            Entry.start_time < end_date,
        ).delete()
        db.session.commit()

    parser = Parser(start_date, end_date)
    created: List[Entry] = []
    for item in entries_data:
        draft = Entry(
            start_time=item["start_time"],
            end_time=item["end_time"],
            title=item["title"],
            project=item["project"],
        )
        resolve_entry_group_project(draft)
        saved = parser.create_entry(draft, None)
        saved.module = MODULE_NAME
        db.session.merge(saved)
        created.append(saved)
    db.session.commit()
    logger.info("Created %s local entries", len(created))
    return created


def populate_local_entries(
    start_date: datetime,
    end_date: datetime,
    replace_existing: bool = True,
) -> List[Entry]:
    """
    Create local entries from commit/session inference and persist them.
    """
    if MODULE_NAME not in settings.ENABLED_MODULES:
        raise ValueError("local module is not enabled")

    if not _has_source_data(start_date, end_date):
        raise ValueError(
            "No source timemodule entries in this range. Fetch activitywatch/git/etc. first."
        )

    allowed_projects = _allowed_local_projects(start_date, end_date)
    if not allowed_projects:
        raise ValueError("No LOCAL projects configured")

    entries_data = build_entries_from_commits(
        start_date, end_date, allowed_projects,
    )
    return persist_local_entries(
        entries_data, start_date, end_date, replace_existing=replace_existing,
    )
