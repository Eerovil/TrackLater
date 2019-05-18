# thyme-toggl-cli

Settings guide

```
ENABLED_MODULES = [
    'thyme',
    'gitmodule',
    'toggl',
    'taiga',
    'jira',
    'slack'
]

TOGGL = {
    'global': {
        API_KEY: 'your-api-key'
    },
    'group1': {
        'NAME': 'First Group',
        'PROJECTS': {
            'Development': 'default',
            'Bug fixing': 'bug',
        }
    },
    'group2': {
        'NAME': 'Second Group',
        'PROJECTS': {
            'Development': 'default',
            'Bug fixing': 'default',
        }
    }
}

GIT = {
    'global': {
        'EMAILS': ['firstname.lastname@email.com'],
    },
    'group1': {
        'REPOS': ['/full/path/to/group1/repo']
    },
    'group2': {
        'REPOS': ['/full/path/to/group2/repo']
    },
}

JIRA = {
    'group1': {
        'CREDENTIALS': ('username', 'password'),
        'URL': 'https://group1.atlassian.net',
        'PROJECT_KEY': 'DEV',
    }
}

TAIGA = {
    'global': {
        'CREDENTIALS': ['username', 'password']
    },
    'group1': {
        'project_slug': 'username-group1'
    },
    'group2': {
        'project_slug': 'username-group2'
    }
}

THYME = {
    'global': {
        'DIR': '/full/path/to/thyme/dir',
    }
}

SLACK = {
    'global': {
        'API_KEY': 'legacy-slack-api-key-global',
        'USER_ID': 'your-user-id',
    },
    'group2': {
        'API_KEY': 'legacy-slack-api-key-group2',
        'USER_ID': 'your-user-id',
    }
}

```
