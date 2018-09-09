from flask import Flask, request, render_template
from thymetogglutil.main import Parser
from datetime import datetime, timedelta
from thymetogglutil import settings
import json
import pytz

app = Flask(__name__)

parser = None

logger = app.logger

@app.route("/")
def hello():
    return render_template(
        'index.html'
    )


@app.route('/sessions', methods=['GET'])
def sessions():
    if request.method == 'GET':
        now = datetime.now()
        parser = Parser(now - timedelta(days=15), now - timedelta(days=0))
        parser.parse()
        return json.dumps({
            'sessions': parser.sessions,
            'time_entries': parser.time_entries,
            'log': parser.log,
            'issues': parser.issues[:100]
        }, default=str)


def parseTimestamp(stamp):
    tz = pytz.timezone('Europe/Helsinki')
    date = datetime.fromtimestamp(int(stamp) / 1e3, tz)
    return date


@app.route('/export', methods=['POST'])
def export():
    if request.method == 'POST':
        parser = Parser(None, None)
        entry = parser.push_session({
            'start_time': parseTimestamp(request.form['start_time']),
            'end_time': parseTimestamp(request.form['end_time']),
        }, request.form['name'], request.form.get('id', None))
        return json.dumps(entry, default=str)


@app.route('/log', methods=['GET'])
def log():
    if request.method == 'GET':
        now = datetime.now()
        parser = Parser(now - timedelta(days=10), now)
        parser.parse_git()
        parser.parse_jira()
        return json.dumps(parser.log, default=str)
