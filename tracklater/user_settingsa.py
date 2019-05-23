ENABLED_MODULES = [
    # 'thyme',
    # 'gitmodule',
     'toggl',
    # 'taiga',
    # 'jira',
    # 'slack',
]

TESTING = False
THREADED = False

UI_SETTINGS = {
    'toggl': {
        'global': '#E01A22'
    },
    'thyme': {
        'global': '#1aef65'
    },
    'gitmodule': {
        'global': '#F44D27'
    },
    'slack': {
        'global': '#4A154B'
    }
}

TOGGL = {
    'global': {
        'API_KEY': '8fbd63aa6de0ba26aee26d44fba7ea75'
    },
    'outdoor': {
        'NAME': 'Scandinavian Outdoor',
        'PROJECTS': {
            'Vikatilanteet': 'bug',
            'Verkkokauppakehitys': 'default',
        }
    },
    'storm': {
        'NAME': 'Storm',
        'PROJECTS': {
            'Vikatilanteet': 'bug',
            'Verkkokauppakehitys': 'default',
        }
    },
    'myssy': {
        'NAME': 'Myssyfarmi',
        'PROJECTS': {
            'Verkkokauppakehitys': 'default',
        }
    }
}

GIT = {
    'global': {
        'EMAILS': ['eero.vilpponen@gmail.com', 'eero.vilpponen@protecomp.fi'],
    },
    'outdoor': {
        'REPOS': ['/home/eero/Documents/outdoor/sos',
                  '/home/eero/Documents/outdoor/tilhi', '/home/eero/Documents/outdoor/soi',
                  '/home/eero/Documents/outdoor/soi/shared-apps']
    },
    'storm': {
        'REPOS': ['/home/eero/Documents/storm']
    },
    'myssy': {
        'REPOS': ['/home/eero/Documents/myssyfarmi']
    },
    'cloudprice': {
        'REPOS': ['/home/eero/Documents/cloudprice']
    },
}

JIRA = {
    'outdoor': {
        'CREDENTIALS': ('eero.vilpponen@protecomp.fi', 'sseSLppOHpnJbHPb97xti2Heri'),
        'URL': 'https://scandinavianoutdoor.atlassian.net',
        'PROJECT_KEY': 'DEV',
    }
}

TAIGA = {
    'global': {
        'CREDENTIALS': ['eerovilpponen', 'wdNn2tkd5Y45kcKt']
    },
    'storm': {
        'project_slug': 'msvilp-storm'
    },
    'myssy': {
        'project_slug': 'msvilp-myssyfarmi'
    }
}

THYME = {
    'global': {
        'DIR': '/home/eero/Documents/thyme',
        'IDLE': 900,
        'CUTOFF': 300,
    }
}

SLACK = {
    'global': {
        'API_KEY': 'xoxp-13389763879-213139729830-627459379153-1b68f049ba0f1b0ec64d42aa44ca8316',
        'USER_ID': 'U6943MFQE',
    },
    'outdoor': {
        'API_KEY': 'xoxp-13373711861-338515366999-627399231185-f4a92786ad0e53ae80b6f9e6dc4d91b0',
        'USER_ID': 'U9YF5ASVD'
    },
}


from test_settings import *