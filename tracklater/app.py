from flask import Flask, request, render_template
from database import db
from main import Parser
import settings
from utils import _str
from datetime import datetime, timedelta, date
import json
import pytz
from typing import Optional, Dict
import os

from requests.models import Response

from models import Entry, Issue, Project, ApiCall  # noqa

from timemodules.interfaces import AddEntryMixin, UpdateEntryMixin

app = Flask(__name__)

logger = app.logger
DIRECTORY = os.path.dirname(os.path.realpath(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}/database.db'.format(DIRECTORY)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()


class State(object):
    parser: Optional[Parser] = None


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        if obj.tzinfo and obj.tzinfo is not pytz.utc:
            logger.warning("Trying to serialize timezone aware date %s", obj)
        obj.replace(tzinfo=None)
        # No idea, but for some reason using isoformat() here did *not* work.
        # Just add utc timezone manually then... (This will make js convert it automatically)
        return obj.isoformat() + "+00:00"
    raise TypeError("Type %s not serializable" % type(obj))


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
        return json.dumps(data, default=json_serial)
    return None


@app.route('/fetchdata', methods=['GET'])
def fetchdata() -> Optional[str]:
    if request.method == 'GET':
        keys = request.values.get('keys[]', 'all')
        parse = request.values.get('parse', '1')
        now = datetime.utcnow()
        if 'from' in request.values:
            from_date = parseTimestamp(request.values['from'])
        else:
            from_date = now - timedelta(days=14)
        if 'to' in request.values:
            to_date = parseTimestamp(request.values['to'])
        else:
            to_date = now

        if getattr(settings, 'OVERRIDE_START', None):
            from_date = settings.OVERRIDE_START
        if getattr(settings, 'OVERRIDE_END', None):
            to_date = settings.OVERRIDE_END

        parser = Parser(from_date, to_date)
        if parse == '1':
            parser.parse()
        data: Dict[str, Dict] = {}
        for key in settings.ENABLED_MODULES:
            if keys == "all" or key in keys:
                data[key] = {}
                data[key]['entries'] = [entry.to_dict()
                                        for entry in Entry.query.filter(
                                            Entry.module == key,
                                            Entry.start_time >= from_date,
                                            Entry.start_time <= to_date
                                        )]
                data[key]['projects'] = [project.to_dict()
                                         for project in Project.query.filter(
                                            Project.module == key
                                        )]
                data[key]['issues'] = [issue.to_dict()
                                       for issue in Issue.query.filter(
                                            Issue.module == key
                                        )]
                data[key]['capabilities'] = parser.modules[key].capabilities
        return json.dumps(data, default=json_serial)
    return None


def parseTimestamp(stamp):
    if not stamp:
        return None
    date = datetime.fromtimestamp(int(stamp) / 1e3)
    return date


@app.route('/updateentry', methods=['POST'])
def updateentry() -> Optional[str]:
    if request.method == 'POST':
        module = request.values.get('module')
        entry_id = _str(request.values.get('entry_id', None))
        project = request.values.get('project_id', None)
        if project == "null":
            project = None
        new_entry = Entry(
            start_time=parseTimestamp(request.values['start_time']),
            end_time=parseTimestamp(request.values.get('end_time', None)),
            id=entry_id,
            issue=request.values.get('issue_id', None),
            project=project,
            title=request.values.get('title', ''),
            text=request.values.get('text', ""),
            extra_data=request.values.get('extra_data', {})
        )
        issue = None
        if new_entry.issue:
            issue = Issue.query.filter(Issue.uuid == new_entry.issue).first()

        parser = Parser(None, None)

        if not entry_id:
            # Check that create is allowed
            assert isinstance(parser.modules[module], AddEntryMixin)
            new_entry = parser.modules[module].create_entry(  # type: ignore
                new_entry=new_entry,
                issue=issue
            )
        else:
            # Check that update is allowed
            assert isinstance(parser.modules[module], UpdateEntryMixin)
            new_entry = parser.modules[module].update_entry(  # type: ignore
                entry_id=new_entry.id,
                new_entry=new_entry,
                issue=issue
            )
        data = "error"

        if new_entry:
            new_entry.module = module
            db.session.merge(new_entry)
            db.session.commit()
            data = new_entry.to_dict()

        return json.dumps(data, default=json_serial)
    return None


@app.route('/deleteentry', methods=['POST'])
def deleteentry() -> Optional[str]:
    if request.method == 'POST':
        module = request.values.get('module')
        entry_id = request.values.get('entry_id')

        parser = Parser(None, None)
        # Check that delete is allowed
        assert isinstance(parser.modules[module], AddEntryMixin)
        ret = parser.modules[module].delete_entry(  # type: ignore
            entry_id=entry_id
        )

        return json.dumps(ret, default=json_serial)
    return None
