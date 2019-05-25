from flask import Flask, request, render_template
from main import Parser
import settings
from utils import _str
from datetime import datetime, timedelta
import json
import pytz
import db

from typing import Optional, Dict

from requests.models import Response

from timemodules.interfaces import Entry, AddEntryMixin, UpdateEntryMixin

app = Flask(__name__)

logger = app.logger

db.init_app(app)


class State(object):
    parser: Optional[Parser] = None


@app.route("/")
def hello() -> Response:
    return render_template(
        'index.html'
    )


@app.route('/listmodules', methods=['GET'])
def listmodules() -> Optional[str]:
    if request.method == 'GET':
        data = {}
        for module_name in settings.ENABLED_MODULES:
            data[module_name] = {
                'color': settings.UI_SETTINGS.get(module_name, {}).get('global', None)
            }
        return json.dumps(data, default=str)
    return None


@app.route('/fetchdata', methods=['GET'])
def fetchdata() -> Optional[str]:
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
        State.parser = parser
        data: Dict[str, Dict] = {}
        for key in settings.ENABLED_MODULES:
            if keys == "all" or key in keys:
                data[key] = {}
                data[key]['entries'] = [entry.to_dict()
                                        for entry in parser.modules[key].entries]
                data[key]['projects'] = [project.to_dict()
                                         for project in parser.modules[key].projects]
                data[key]['issues'] = [issue.to_dict()
                                       for issue in parser.modules[key].issues]
                data[key]['capabilities'] = parser.modules[key].capabilities
        return json.dumps(data, default=str)
    return None


def parseTimestamp(stamp):
    if not stamp:
        return None
    tz = pytz.timezone(settings.TIMEZONE)
    date = datetime.fromtimestamp(int(stamp) / 1e3, tz)
    return date


@app.route('/updateentry', methods=['POST'])
def updateentry() -> Optional[str]:
    if State.parser is None:
        return "Run fetchdata first"
    if request.method == 'POST':
        module = request.values.get('module')
        entry_id = _str(request.values.get('entry_id', None))
        new_entry = Entry(
            start_time=parseTimestamp(request.values['start_time']),
            end_time=parseTimestamp(request.values.get('end_time', None)),
            id=entry_id,
            issue=request.values.get('issue_id', None),
            project=request.values['project_id'],
            title=request.values.get('title', ''),
            text=request.values.get('text', []),
            extra_data=request.values.get('extra_data', {})
        )
        issue = None
        if new_entry.issue:
            for _module in settings.ENABLED_MODULES:
                if 'issues' not in State.parser.modules[_module].capabilities:
                    continue
                _tmp = State.parser.modules[_module].find_issue(new_entry.issue)  # type: ignore
                if _tmp:
                    issue = _tmp
                    break

        if not entry_id:
            # Check that create is allowed
            assert isinstance(State.parser.modules[module], AddEntryMixin)
            entry_id = State.parser.modules[module].create_entry(  # type: ignore
                new_entry=new_entry,
                issue=issue
            )
        else:
            # Check that update is allowed
            assert isinstance(State.parser.modules[module], UpdateEntryMixin)
            State.parser.modules[module].update_entry(  # type: ignore
                entry_id=new_entry.id,
                new_entry=new_entry,
                issue=issue
            )

        data = [
            entry.to_dict()
            for entry in State.parser.modules[module].entries
            if entry.id == entry_id
        ][0]
        return json.dumps(data, default=str)
    return None


@app.route('/deleteentry', methods=['POST'])
def deleteentry() -> Optional[str]:
    if State.parser is None:
        return "Run fetchdata first"
    if request.method == 'POST':
        module = request.values.get('module')
        entry_id = request.values.get('entry_id')

        # Check that delete is allowed
        assert isinstance(State.parser.modules[module], AddEntryMixin)
        ret = State.parser.modules[module].delete_entry(  # type: ignore
            entry_id=entry_id
        )

        return json.dumps(ret, default=str)
    return None
