
TESTING = True

ENABLED_MODULES = ['jira', 'gitmodule', 'slack', 'taiga', 'toggl', 'thyme']

# Test settings for Jira
JIRA = {
    'group1': {
        'CREDENTIALS': ('', ''),
        'URL': 'mock://jira.test',
        'PROJECT_KEY': 'TEST',
    }
}

# Test settings for Git
GIT = {
    'global': {
        'EMAILS': ['test.person@email.com'],
    },
    'group1': {
        'REPOS': ['path1', 'path2']
    },
    'group2': {
        'REPOS': ['path3']
    },
}

# Test settings for Slack
SLACK = {
    'global': {
        'API_KEY': '',
        'USER_ID': '1',
    }
}

# Test settings for Slack
TAIGA = {
    'global': {
        'CREDENTIALS': 'test'
    },
    'group2': {
        'project_slug': 'test'
    }
}

TOGGL = {
    'global': {
        'API_KEY': 'your-api-key'
    },
    'group1': {
        'NAME': 'First Client',
        'PROJECTS': {
            'Development': 'default',
            'Bug fixing': 'bug',
        }
    },
    'group2': {
        'NAME': 'Second Client',
        'PROJECTS': {
            'Development': 'default',
            'Bug fixing': 'default',
        }
    }
}

THYME = {
    'global': {
    }
}
