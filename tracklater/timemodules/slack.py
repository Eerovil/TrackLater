
from slack import WebClient
from datetime import datetime
import pytz
from typing import List

from tracklater import settings
from .interfaces import EntryMixin, AbstractParser, AbstractProvider
from tracklater.models import Entry

import logging
logger = logging.getLogger(__name__)


class Parser(EntryMixin, AbstractParser):

    def get_entries(self) -> List[Entry]:
        # start_date, end_date = self.get_offset_dates()
        # if not start_date and not end_date:
        #     return []
        start_date = self.start_date
        end_date = self.end_date
        entries = []
        for group, group_data in settings.SLACK.items():

            slack_token = group_data['API_KEY']
            user_id = group_data['USER_ID']

            provider = Provider(slack_token)
            users_list = provider.api_call("users.list")
            users = {}
            for user in users_list['members']:
                users[user['id']] = (
                    user['profile'].get('first_name', 'NULL') + ' ' +
                    user['profile'].get('last_name', 'NULL')
                )
            channels = provider.api_call(
                "conversations.list", data={'types': 'public_channel,private_channel,mpim,im'}
            )['channels']
            for channel in channels:
                history = provider.api_call(
                    "conversations.history",
                    data={
                        'channel': channel['id'],
                        'oldest': (start_date - datetime(1970, 1, 1)).total_seconds(),
                        'latest': (end_date - datetime(1970, 1, 1)).total_seconds()
                    }
                )

                # Get either Istant Message recipient or channel name
                if channel.get('is_im', False) and channel.get('user', ''):
                    channel_info = users.get(channel.get('user', ''), None)
                else:
                    channel_info = channel.get('name_normalized', 'Unknown')

                for message in history['messages']:
                    if message.get('user', '') == user_id:
                        start_time = datetime.fromtimestamp(float(message['ts']))
                        # "Guess" That the timestamp has an offset equal to settings.TIMEZONE
                        if getattr(settings, 'TIMEZONE', None):
                            start_time = pytz.timezone("Europe/Helsinki").localize(
                                start_time
                            ).astimezone(pytz.utc).replace(tzinfo=None)
                        # Replace @User id with the name
                        for _user_id in users.keys():
                            if _user_id in message['text']:
                                message['text'] = message['text'].replace(
                                    _user_id, users[_user_id]
                                )
                        entries.append(Entry(
                            start_time=start_time,
                            title='',
                            text="{} - {} \n {}".format(group, channel_info, message['text'])
                        ))
        return entries


class Provider(AbstractProvider):
    def __init__(self, slack_token):
        self.sc = WebClient(slack_token)

    def api_call(self, *args, **kwargs):
        return self.sc.api_call(*args, **kwargs)

    def test_api_call(self, *args, **kwargs):
        if args[0] == "users.list":
            return {
                "members": [
                    {
                        "id": "1",
                        "profile": {
                            "first_name": "Firstname",
                            "last_name": "Lastename"
                        }
                    },
                    {
                        "id": "2",
                        "profile": {
                            "first_name": "Secondname",
                            "last_name": "Lastename"
                        }
                    }
                ]
            }
        if args[0] == "conversations.list":
            return {"channels": [{"id": "1"}]}
        if args[0] == "conversations.history":
            return {
                "messages": [
                    {
                        "user": "1",
                        "text": "First Message",
                        "ts": "1234567"
                    },
                    {
                        "user": "1",
                        "text": "Second Message",
                        "ts": "1234568"
                    },
                    {
                        "user": "2",
                        "text": "Third Message",
                        "ts": "1234569"
                    }
                ]
            }
