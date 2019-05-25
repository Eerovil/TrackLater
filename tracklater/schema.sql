-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS entries;
DROP TABLE IF EXISTS issues;
DROP TABLE IF EXISTS projects;

CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TIMESTAMP NOT NULL,
    entry_id TEXT NULL,
    end_time TIMESTAMP NULL,
    date_group TEXT NULL,
    issue_id INTEGER NULL,
    group_slug TEXT NULL,
    project_id INTEGER NULL,
    title TEXT NULL,
    text TEXT NULL,
    extra_data TEXT NULL,
    FOREIGN KEY (issue_id) REFERENCES issues (id),
    FOREIGN KEY (project_id) REFERENCES projects (id)
);

CREATE TABLE issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NULL,
    title TEXT NULL,
    group_slug TEXT NULL,
    uuid TEXT NULL,
    extra_data TEXT NULL
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pid TEXT NULL,
    group_slug TEXT NULL
);
