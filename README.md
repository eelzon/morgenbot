# Morgenbot
### A [Slack](https://slack.com/) standup bot

## Installation

1. Clone the repo
2. `pip install -r requirements.txt`
3. Host the web app on [Heroku](http://heroku.com):
```
heroku create
git push heroku master
heroku ps:scale web=1
heroku logs
```
4. Set up some config variables:
```
heroku config:set TOKEN=<your team's Slack API token> (required)
heroku config:set USERNAME=<your bot's username> (optional; defaults to 'morgenbot')
heroku config:set ICON_EMOJI=<the emoji used in the bot's icon> (optional; defaults to ':coffee:')
heroku config:set CHANNEL=<the channel in which you stand up> (optional; defaults to '#standup')
heroku config:set IGNORE_USERS=<list of strings representing channel users who never stand up> (optional; defaults to [])
```
5. Add the URL where you deployed the web app as an [outgoing webhook](https://my.slack.com/services/new/outgoing-webhook) in Slack. Don't forget the trailing `/`!
6. Type `!standup` in your chosen channel to start a new standup. (Need help? Type `!help`.)

## Thanks


## Contributors

* @eelzon