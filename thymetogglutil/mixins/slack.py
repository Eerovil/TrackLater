
from slackclient import SlackClient
from thymetogglutil import settings
from datetime import datetime
from thymetogglutil.utils import FixedOffset


class SlackMixin(object):

    def parse_slack(self):
        for workspace in settings.SLACK_WORKSPACES:

            slack_token = workspace['API_KEY']
            user_id = workspace['USER_ID']

            sc = SlackClient(slack_token)

            users_list = sc.api_call("users.list")
            users = {}
            for user in users_list['members']:
                users[user['id']] = (
                    user['profile'].get('first_name', 'NULL') + ' ' +
                    user['profile'].get('last_name', 'NULL')
                )

            for channel in sc.api_call("conversations.list",
                                       types='public_channel,private_channel,mpim,im')['channels']:
                history = sc.api_call(
                    "conversations.history", channel=channel['id'],
                    oldest=(self.start_date - datetime(1970, 1, 1)).total_seconds(),
                    latest=(self.end_date - datetime(1970, 1, 1)).total_seconds()
                )

                # Get either Istant Message recipient or channel name
                if channel['is_im'] and channel.get('user', ''):
                    channel_info = users.get(channel.get('user', ''), None)
                else:
                    channel_info = channel.get('name_normalized', 'Unknown')

                for message in history['messages']:
                    if message.get('user', '') == user_id:
                        message['info'] = u'{} - {}'.format(workspace['NAME'],
                                                            channel_info)
                        message['time'] = datetime.fromtimestamp(
                            float(message['ts']), tz=FixedOffset(0, 'Helsinki')
                        )
                        # Replace @User id with the name
                        for _user_id in users.keys():
                            if _user_id in message['text']:
                                message['text'] = message['text'].replace(
                                    _user_id, users[_user_id]
                                )
                        self.slack_messages.append(message)
                        print(message)
