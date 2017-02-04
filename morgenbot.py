import os
import re
import sys
import traceback
import json
import datetime
import time
import random
import urllib2

from slacker import Slacker

from flask import Flask, request
app = Flask(__name__)

curdir = os.path.dirname(os.path.abspath(__file__))
os.chdir(curdir)

slack = Slacker(os.getenv('TOKEN'))
username = os.getenv('USERNAME', 'morgenbot')
icon_emoji = os.getenv('ICON_EMOJI', ':coffee:')
channel = os.getenv('CHANNEL', '#standup')
ignore_users = os.getenv('IGNORE_USERS', '[]')

init_greeting = os.getenv('INIT_GREETING', 'Good morning!')
start_message = os.getenv('START_MESSAGE', 'What did you work on yesterday? What are you working on today? What, if any, are your blockers?')

giphy = True if os.getenv('GIPHY', 'false').lower() == 'true' else False

commands = ['standup','start','cancel','next','skip','later','table','left','ignore','heed','ignoring','ready','help']

users = []
topics = []
time = []
in_progress = False
current_user = ''
absent_users = []

def post_message(text, attachments=[]):
    slack.chat.post_message(channel     = channel,
                            text        = text,
                            username    = username,
                            parse       = 'full',
                            link_names  = 1,
                            attachments = attachments,
                            icon_emoji  = icon_emoji)

def get_user(id):
    user = slack.users.info(id).body
    return user['user']['name']

def get_channel(id):
    channel = slack.channels.info(id).body
    return channel['channel']['name']

def init():
    global users
    global topics
    global time
    global in_progress

    if len(users) != 0:
        post_message('Looks like we have a standup already in process.')
        return
    users = standup_users()
    topics = []
    time = []
    in_progress = True
    post_message('%s, @channel! Please type !start when you are ready to stand up.' % init_greeting)

def start():
    global time

    if len(time) != 0:
        post_message('But we\'ve already started!')
        return
    time.append(datetime.datetime.now())
    post_message('Let\'s get started! %s\nWhen you\'re done, please type !next' % start_message)
    next()

def cancel():
    tabled()
    post_message('Standup is cancelled. Bye!')
    reset()

def done():
    global time

    time.append(datetime.datetime.now())
    standup_time()
    tabled()
    post_message('Bye!')
    reset()

def reset():
    global users
    global topics
    global time
    global in_progress
    global current_user

    del users[:]
    del topics[:]
    del time[:]
    in_progress = False
    current_user = ''

def standup_users():
    global ignore_users
    global absent_users

    ignore_users_array = eval(ignore_users)

    channel_id = '';
    channel_name = channel.replace('#', '') # for some reason we skip the # in this API call
    all_channels = slack.channels.list(1) # 1 means we skip any archived rooms
    for one_channel in all_channels.body['channels']:
        if one_channel['name'] == channel_name:
            channel_id = one_channel['id']

    standup_room = slack.channels.info(channel_id).body['channel']
    standup_users = standup_room['members']
    active_users = []

    for user_id in standup_users:
        user_name = slack.users.info(user_id).body['user']['name']
        is_deleted = slack.users.info(user_id).body['user']['deleted']
        if not is_deleted and user_name not in ignore_users_array and user_name not in absent_users:
            active_users.append(user_name)

    # don't forget to shuffle so we don't go in the same order every day!
    random.shuffle(active_users)

    return active_users

def next():
    global users
    global current_user

    if len(users) == 0:
        done()
    else:
        current_user = users.pop()
        post_message('@%s, you\'re up' % current_user)

def standup_time():
    if len(time) != 2: return
    seconds = (time[1] - time[0]).total_seconds()
    minutes = seconds / 60
    post_message('That\'s everyone! Standup took us %d minutes.' % minutes)

def left():
    if len(users) == 0:
        post_message('That\'s everyone!')
    else:
        post_message('Here\'s who\'s left: @' + ', @'.join(users))

def ignore(user):
    global ignore_users
    global absent_users
    active_users = standup_users()

    if user == '':
        post_message('Who should I ignore?')
        return

    user = user[1:]
    if user not in active_users and user not in ignore_users and user not in absent_users:
        post_message('I don\'t recognize that user.')
    elif user in ignore_users or user in absent_users:
        post_message('I\'m already ignoring that user.')
    elif user in active_users:
        absent_users.append(user)
        post_message('I won\'t call on @%s again until I am told to using !heed <username>.' % user)

def heed(user):
    global ignore_users
    global absent_users
    active_users = standup_users()

    if user == '':
        post_message('Who should I heed?')
        return

    user = user[1:]
    if user not in active_users and user not in ignore_users and user not in absent_users:
        post_message('I don\'t recognize that user.')
    elif user in ignore_users:
        post_message('We never call on that user. Try asking my admin to heed that username.')
    elif user in active_users:
        post_message('I\'m not ignoring that user.')
    elif user in absent_users:
        absent_users.remove(user)
        post_message('I\'ll start calling on @%s again at the next standup.' % user)

def ignoring():
    global ignore_users
    global absent_users

    if len(ignore_users) == 0 and len(absent_users) == 0:
        post_message('We\'re not ignoring anyone.')
        return

    if len(ignore_users) != 0:
        post_message('Here\'s who we never call on: ' + ignore_users)
    if len(absent_users) != 0:
        post_message('Here\'s who we\'re ignoring for now: ' + ', '.join(absent_users))

def skip():
    post_message('Skipping @%s.' % current_user)
    next()
    
def later():
    post_message('We\'ll call on @%s later.' % current_user)
    users.append(current_user)
    next()

def table(topic_user, topic):
    global topics

    channels = re.findall(r"<#(.*?)>", topic)
    users = re.findall(r"<@(.*?)>", topic)

    for channel in channels:
        channel_name = get_channel(channel)
        topic = topic.replace('<#%s>' % channel, '#%s' % channel_name)

    for user in users:
        user_name = get_user(user)
        topic = topic.replace('<@%s>' % user, '@%s' % user_name)

    post_message('@%s: Tabled.' % topic_user)
    topics.append(str(topic))

def tabled():
    if len(topics) == 0: return
    post_message('Tabled topics:')
    for topic in topics:
        post_message('-%s' % topic)

def giphy(text):
    url = 'http://api.giphy.com/v1/gifs/search?q=%s&api_key=dc6zaTOxFJmzC&limit=1' % urllib2.quote(text.encode("utf8"))
    response = urllib2.urlopen(url)
    data = json.loads(response.read())

    if len(data['data']) == 0:
        post_message('Not sure what "%s" is.' % text)
    else:
        attachments = [{
            'fallback': text,
            'title': text,
            'title_link': data['data'][0]['url'],
            'image_url': data['data'][0]['images']['fixed_height']['url']
        }]

        post_message('Not sure what "%s" is.' % text, json.dumps(attachments))

def ready(msguser):
    global ignore_users
    global absent_users
    global current_user
    global users
    active_users = standup_users()

    if msguser == '':
        post_message('Your username is blank. Are you a ghost?')
        return

    if msguser not in active_users and msguser not in ignore_users and msguser not in absent_users:
        post_message('I don\'t recognize you. How did you get in here?')
    elif msguser in ignore_users:
        post_message('I\'m ignoring you. Try asking my admin to heed you.')
    elif msguser in absent_users:
        post_message('I\'ll come back to you, @%s' % current_user)
        users.append(current_user)
        current_user = msguser
        absent_users.remove(msguser)
        post_message('Welcome back, @%s. We will call on you from now on.' % msguser)
    elif msguser in users:
        post_message('I\'ll come back to you, @%s' % current_user)
        users.append(current_user)
        current_user = msguser
        users.remove(msguser)
        post_message('Alright @%s, go ahead' % msguser)
    elif msguser == current_user:
        post_message('It\'s already your turn. Go ahead.')
    else:
        post_message('You already went during this standup')

def help(topic=''):
    if topic == '':
        post_message('My commands are !standup, !start, !cancel, !next, !ready, !skip, !later, !table, !left, !ignore, !heed, and !ignoring.\nAsk me "!help <command> to learn what they do.')
        return

    topic = topic[1:]
    if topic == 'standup' or topic == '!standup':
        post_message('Type !standup to initiate a new standup')
    elif topic == 'start' or topic == '!start':
        post_message('Type !start to get started with standup once everyone is ready')
    elif topic == 'cancel' or topic == '!cancel':
        post_message('Type !cancel if you\'d like to stop the standup entirely.')
    elif topic == 'next' or topic == '!next':
        post_message('Type !next to call on the next person when you\'re done standing up')
    elif topic == 'skip' or topic == '!skip':
        post_message('Type !skip to skip someone who isn\'t standing up that day')
    elif topic == 'later' or topic == '!later':
        post_message('Type !later to move someone who isn\'t ready yet to the end of the list')
    elif topic == 'table' or topic == '!table':
        post_message('Type !table <topic> to save a topic for later discussion. I\'ll list these for you when standup is over.')
    elif topic == 'left' or topic == '!left':
        post_message('Type !left to find out who is left in the standup')
    elif topic == 'ignore' or topic == '!ignore':
        post_message('Type !ignore <username> to temporarily skip a user during standup for a while')
    elif topic == 'heed' or topic == '!heed':
        post_message('Type !heed <username> to add an ignored user back, starting with the next standup')
    elif topic == 'ignoring' or topic == '!ignoring':
        post_message('Type !ignoring to find out who we\'re skipping over for standups')
    elif topic == 'ready' or topic == '!ready':
        post_message('Type !ready to skip ahead in the queue and give your standup immediately')
    else:
        post_message('Not sure what "%s" is.' % topic)
        if giphy:
            post_message('/giphy %s' % topic)

@app.route("/", methods=['POST'])
def main():
    # ignore message we sent
    msguser = request.form.get("user_name", "").strip()
    if msguser == username or msguser.lower() == "slackbot": return

    text = request.form.get("text", "")

    match = re.findall(r"^!(\S+)", text)
    if not match: return

    command = match[0]
    args = text[text.find("!%s" % command) + len(command) + 1:]
    command = command.lower()

    if command not in commands:
        if giphy:
            giphy("%s %s" % (command, args))
        else:
            post_message('Not sure what "%s" is.' % command)
        return json.dumps({ })
    elif not in_progress and command != 'standup' and command != 'help' and command != 'ignore' and command != 'heed' and command != 'ignoring':
        post_message('Looks like standup hasn\'t started yet. Type !standup.')
        return json.dumps({ })

    if command == 'standup':
        init()
    elif command == 'start':
        start()
    elif command == 'cancel':
        cancel()
    elif command == 'next':
        next()
    elif command == 'skip':
        skip()
    elif command == 'later':
        later()
    elif command == 'table':
        table(msguser, args)
    elif command == 'left':
        left()
    elif command == 'ignore':
        ignore(args)
    elif command == 'heed':
        heed(args)
    elif command == 'ignoring':
        ignoring()
    elif command == 'help':
        help(args)
    elif command == 'ready':
        ready(msguser)
        
    return json.dumps({ })

if __name__ == "__main__":
    app.run(debug=True)
