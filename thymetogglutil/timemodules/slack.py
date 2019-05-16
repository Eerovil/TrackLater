
from slack import WebClient
from thymetogglutil import settings
from datetime import datetime
from thymetogglutil.utils import FixedOffset
from thymetogglutil.timemodules.interfaces import Entry, EntryMixin, AbstractParser


class Parser(EntryMixin, AbstractParser):

    def get_entries(self):
        entries = []
        for group, group_data in settings.SLACK.items():

            slack_token = group_data['API_KEY']
            user_id = group_data['USER_ID']

            sc = WebClient(slack_token)

            users_list = sc.api_call("users.list")
            users = {}
            for user in users_list['members']:
                users[user['id']] = (
                    user['profile'].get('first_name', 'NULL') + ' ' +
                    user['profile'].get('last_name', 'NULL')
                )
            channels = sc.api_call(
                "conversations.list", data={'types': 'public_channel,private_channel,mpim,im'}
            )['channels']
            for channel in channels:
                history = sc.api_call(
                    "conversations.history",
                    data={
                        'channel': channel['id'],
                        'oldest': (self.start_date - datetime(1970, 1, 1)).total_seconds(),
                        'latest': (self.end_date - datetime(1970, 1, 1)).total_seconds()
                    }
                )

                # Get either Istant Message recipient or channel name
                if channel['is_im'] and channel.get('user', ''):
                    channel_info = users.get(channel.get('user', ''), None)
                else:
                    channel_info = channel.get('name_normalized', 'Unknown')

                for message in history['messages']:
                    if message.get('user', '') == user_id:
                        start_time = datetime.fromtimestamp(
                            float(message['ts']), tz=FixedOffset(0, 'Helsinki')
                        )
                        # Replace @User id with the name
                        for _user_id in users.keys():
                            if _user_id in message['text']:
                                message['text'] = message['text'].replace(
                                    _user_id, users[_user_id]
                                )
                        entries.append(Entry(
                            start_time=start_time,
                            title='',
                            text=['{} - {}'.format(group, channel_info), message['text']]
                        ))
        return entries
