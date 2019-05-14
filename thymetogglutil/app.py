from flask import Flask, request, render_template
from thymetogglutil.main import Parser
from thymetogglutil import settings
from datetime import datetime, timedelta
from dataclasses import asdict
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


@app.route('/listmodules', methods=['GET'])
def listmodules():
    if request.method == 'GET':
        data = settings.ENABLED_TIMEMODULES + settings.ENABLED_ISSUEMODULES
        return json.dumps(data, default=str)


@app.route('/fetchdata', methods=['GET'])
def fetchdata():
    if request.method == 'GET':
        keys = request.values.get('keys[]', 'all')
        now = datetime.now()
        if 'from' in request.values:
            from_date = parseTimestamp(request.values['from'])
        else:
            from_date = now - timedelta(days=14)

        if 'to' in request.values:
            to_date = parseTimestamp(request.values['to'])
        else:
            to_date = now

        parser = Parser(from_date, to_date)
        parser.parse()
        data = {}
        for key in settings.ENABLED_TIMEMODULES:
            if keys == "all" or key in keys:
                data[key] = {}
                data[key]['entries'] = [entry.to_dict()
                                        for entry in parser.modules[key].entries]
                data[key]['projects'] = [project.to_dict()
                                         for project in parser.modules[key].projects]
        for key in settings.ENABLED_ISSUEMODULES:
            if keys == "all" or key in keys:
                data[key] = {}
                data[key]['issues'] = [issue.to_dict()
                                       for issue in parser.modules[key].issues]
        return json.dumps(data, default=str)


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
        }, request.form['name'], request.form.get('id', None), request.form.get('project', None))
        return json.dumps(entry, default=str)


@app.route('/delete', methods=['POST'])
def delete():
    if request.method == 'POST':
        parser = Parser(None, None)
        ret = parser.delete_time_entry(request.form.get('id'))
        return json.dumps(ret, default=str)


@app.route('/split', methods=['POST'])
def split():
    if request.method == 'POST':
        parser = Parser(None, None)
        (entry1, entry2) = parser.split_time_entry(
            request.form.get('id'),
            parseTimestamp(request.form['start_time']),
            parseTimestamp(request.form['split_time']),
            parseTimestamp(request.form['end_time']),
            request.form.get('name')
        )
        return json.dumps({'entry1': entry1, 'entry2': entry2}, default=str)


@app.route('/log', methods=['GET'])
def log():
    if request.method == 'GET':
        now = datetime.now()
        parser = Parser(now - timedelta(days=10), now)
        parser.parse_git()
        parser.parse_jira()
        return json.dumps(parser.log, default=str)
