import uuid
from typing import List, Optional, cast, Any

from tracklater import settings
from tracklater.models import Entry, Project, Issue
from .interfaces import (
    EntryMixin, AddEntryMixin, UpdateEntryMixin, DeleteEntryMixin, ProjectMixin,
    AbstractParser,
)

import logging
logger = logging.getLogger(__name__)

MODULE_NAME = 'local'


def get_setting(key, default=None, group='global'):
    return settings.helper('LOCAL', key, group=group, default=default)


def default_project_pid(group: str) -> Optional[str]:
    """Default LOCAL project for a group (skips Vikatilanteet-style names)."""
    local_settings = cast(Any, getattr(settings, 'LOCAL', {}))
    data = local_settings.get(group, {})
    if not isinstance(data, dict):
        return None
    for project_name in data.get('PROJECTS', {}):
        if 'vika' in project_name.lower():
            continue
        return '{}:{}'.format(group, project_name)
    projects = data.get('PROJECTS', {})
    if projects:
        project_name = next(iter(projects))
        return '{}:{}'.format(group, project_name)
    return None


def resolve_entry_group_project(entry: Entry) -> Entry:
    if entry.project and not entry.group:
        pid = str(entry.project)
        if ':' in pid:
            entry.group = pid.split(':', 1)[0]
    if entry.group and not entry.project:
        entry.project = default_project_pid(entry.group)
    return entry


class Parser(EntryMixin, AddEntryMixin, UpdateEntryMixin, DeleteEntryMixin, ProjectMixin,
             AbstractParser):
    """
    Local-only time entries: create, update, and delete in TrackLater without
    syncing to an external service. Entries are stored in the app database.
    """

    def get_entries(self) -> List[Entry]:
        if not self.start_date or not self.end_date:
            return []
        rows = Entry.query.filter(
            Entry.module == MODULE_NAME,
            Entry.start_time >= self.start_date,
            Entry.start_time <= self.end_date,
        ).all()
        entries = []
        for row in rows:
            entry = Entry(
                id=row.id,
                start_time=row.start_time,
                end_time=row.end_time,
                title=row.title or '',
                project=row.project,
                group=row.group,
                issue=row.issue,
                text=row.text or '',
                extra_data=row.extra_data,
            )
            entries.append(resolve_entry_group_project(entry))
        return entries

    def get_projects(self) -> List[Project]:
        projects = []
        local_settings = cast(Any, getattr(settings, 'LOCAL', {}))
        for group, data in local_settings.items():
            if group == 'global' or not isinstance(data, dict):
                continue
            client_name = data.get('NAME', group)
            for project_name in data.get('PROJECTS', {}):
                pid = '{}:{}'.format(group, project_name)
                projects.append(Project(
                    pid=pid,
                    title='{} - {}'.format(client_name, project_name),
                    group=group,
                ))
        return projects

    def create_entry(self, new_entry: Entry, issue: Optional[Issue]) -> Entry:
        if issue and issue.group:
            new_entry.group = issue.group
        resolve_entry_group_project(new_entry)
        return Entry(
            id=str(uuid.uuid4()),
            start_time=new_entry.start_time,
            end_time=new_entry.end_time,
            title=new_entry.title,
            project=new_entry.project,
            group=new_entry.group,
        )

    def update_entry(self, entry_id: str, new_entry: Entry, issue: Optional[Issue]) -> Entry:
        if issue and issue.group:
            new_entry.group = issue.group
        resolve_entry_group_project(new_entry)
        return Entry(
            id=entry_id,
            start_time=new_entry.start_time,
            end_time=new_entry.end_time,
            title=new_entry.title,
            project=new_entry.project,
            group=new_entry.group,
        )

    def delete_entry(self, entry_id: str) -> None:
        for i, entry in enumerate(self.entries):
            if entry.id == str(entry_id):
                del self.entries[i]
                break
