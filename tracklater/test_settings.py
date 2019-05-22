
TESTING = True

ENABLED_MODULES = ['jira', 'gitmodule', 'slack']

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
