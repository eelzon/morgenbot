import os
import re
import sys
import traceback
import json
import datetime
import time
import random
from slacker import Slacker

from flask import Flask, request
app = Flask(__name__)

curdir = os.path.dirname(os.path.abspath(__file__))
os.chdir(curdir)

slack = Slacker(os.environ['TOKEN'])
users = []
parked = []
start_time = 0
end_time = 0
channel = os.environ['CHANNEL'] if 'CHANNEL' in os.environ.keys() else '#standup'
username = os.environ['USERNAME'] if 'USERNAME' in os.environ.keys() else 'morgenbot'
icon_emoji = os.environ['ICON_EMOJI'] if 'ICON_EMOJI' in os.environ.keys() else ':coffee:'

def post_message(text):
	slack.chat.post_message(channel = channel, 
							text = text, 
							username = username, 
							icon_emoji = icon_emoji)
							
def standup_users():
	ignore_users = os.environ['IGNORE_USERS'] if 'IGNORE_USERS' in os.environ.keys() else []
	standup_room = slack.channels.info('C02PH2P0Y').body['channel']
	standup_users = standup_room['members']
	active_users = []
	
	for user_data in standup_users:
		user_name = slack.users.info(user_data).body['user']['name']
		if user_name not in ignore_users:
			active_users.append(user_name)
	# don't forget to shuffle so we don't go in the same order every day!
	return random.shuffle(active_users)
							
def next():
	if len(users) == 0:
		end_time = datetime.datetime.now()
		post_message('That\'s everyone! Standup took us %s minutes.' % standup_time())
		if len(parked) != 0:
			parked()
		post_message('Bye!')
	else:
		post_message('%s, you\'re up' % users.pop())
		
def standup_time():
	duration = end_time - start_time
	seconds = duration.seconds
	minutes = seconds / 60
	return minutes
	
def left():
	post_message('Here\'s who\'s left: ' + ', '.join(users))
	
def skip(skipped):
	post_message('Skipping %s.' % skipped)
	next()
	
def park(topic):
	parked.append(topic)
		
def parked():
	post_message('Parked topics:')
	for topic in parked:
		post_message('- %s' % topic)
		
def help(topic=''):
	if topic == '':
		post_message('My commands are !standup, !start, !cancel, !next, !skip, !park, and !left.\nAsk me "!help <command> to learn what they do.')
	elif topic == 'standup' or topic == '!standup':
		post_message('Type !standup to initiate a new standup')
	elif topic == 'start' or topic == '!start':
		post_message('Type !start to get started with standup once everyone is ready')
	elif topic == 'cancel' or topic == '!cancel':
		post_message('Type !cancel if you\'d like to stop the standup entirely.')
	elif topic == 'next' or topic == '!next':
		post_message('Type !next to call on the next person when you\'re done standing up')
	elif topic == 'skip' or topic == '!skip':
		post_message('Type !skip to skip someone who isn\'t standing up that day')
	elif topic == 'park' or topic == '!park':
		post_message('Type !park to save a topic for later discussion. I\'ll list these for you when standup is over.')
	elif topic == 'left' or topic == '!left':
		post_message('Type !left to find out who is left in the standup')
	else:
		post_message('Not sure what %s is.' % topic)
	
@app.route("/", methods=['POST'])
def main():
	# ignore message we sent
	msguser = request.form.get("user_name", "").strip()
	if msguser == username or msguser.lower() == "slackbot": return

	text = request.form.get("text", "")

	# ignore if it doesn't start with !
	match = re.findall(r"!(\S+)", text)
	if not match: return

	command = match[0]
	args = text.replace("!%s" % match[0], '')

	if command == 'standup':
		users = standup_users()
		parked = []
		post_message('Good morning, @channel! Please type !start when you are ready to stand up.')
	elif command == 'start':
		start_time = datetime.datetime.now()
		post_message('Let\'s get started! What did you work on yesterday? What are you working on today? What, if any, are your blockers?\nWhen you\'re done, please type !next')
		next()
	elif command == 'cancel':
		post_message('Standup is cancelled. Bye!')
	elif command == 'next':
		next()
	elif command == 'skip':
		skip(args)
	elif command == 'park':
		park(args)
	elif command == 'left':
		left()
	elif commant == 'help':
		help(args)
		
	return json.dumps({ })

if __name__ == "__main__":
    app.run(debug=True)
