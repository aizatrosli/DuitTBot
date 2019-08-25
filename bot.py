#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, io, json, time
from datetime import datetime, timedelta
from base import *
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging, telegram
import pandas as pd
import numpy as np

token = ""

with open('token.json') as json_file:
	data = json.load(json_file)
	token = data['apikey']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)
duitdb = pd.HDFStore('duitdb.h5')

'''workaround for longlist
if len(args[0]) > 0:
	message = ["[{0}] {1}".format(key,val) for key, val in chat_data['DICTITEMS'].items()]
	for text in message:
		if str(args[0]) in text:
			newmessage.append(text)
msgs = [newmessage[i:i + 10] for i in range(0, len(newmessage), 10)]
for text in msgs:
	update.message.reply_text(text=.join(text))
'''


def spend(bot, update, args, chat_data):
	keyboard = [[
		InlineKeyboardButton("Current Spend", callback_data='current'),
		InlineKeyboardButton("Weekly Spend", callback_data='weekly'),
		InlineKeyboardButton("Monthly Spend", callback_data='monthly')
		]]
	reply_markup = InlineKeyboardMarkup(keyboard)
	update.message.reply_text("Bank Menu", reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)


def spenddecision(bot, update):
	query = update.callback_query
	chat_id = query.message.chat_id
	if 'current' in query.data:
		bot.edit_message_text(text="Add", chat_id=chat_id, message_id=query.message.message_id)
	elif 'weekly' in query.data:
		bot.edit_message_text(text="Remove", chat_id=chat_id, message_id=query.message.message_id)
	elif 'monthly' in query.data:
		bot.edit_message_text(text="Remove", chat_id=chat_id, message_id=query.message.message_id)
	else:
		bot.edit_message_text(text="Unexpected input", chat_id=chat_id, message_id=query.message.message_id)


def bank(bot, update, args, chat_data):
	keyboard = [[
		InlineKeyboardButton("Current Bank", callback_data='current'),
		InlineKeyboardButton("Refresh Bank", callback_data='refresh')
		]]
	reply_markup = InlineKeyboardMarkup(keyboard)
	update.message.reply_text("Bank Menu", reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)


def bankdecision(bot, update):
	query = update.callback_query
	chat_id = query.message.chat_id
	if 'current' in query.data:
		bot.edit_message_text(text="Add", chat_id=chat_id, message_id=query.message.message_id)
	elif 'refresh' in query.data:
		bot.edit_message_text(text="Remove", chat_id=chat_id, message_id=query.message.message_id)
	else:
		bot.edit_message_text(text="Unexpected input", chat_id=chat_id, message_id=query.message.message_id)


def start(bot, update, chat_data):
	user_id = str(update.message.from_user.id)
	username = update.message.from_user.username
	chat_data['test'] = "aylmao"
	update.message.reply_text('Welcome to DuitTBot, {0}!\nLoading user data...'.format(username))
	if "/"+user_id in duitdb.keys():
		latestdata = duitdb[user_id].tail(1)
		update.message.reply_text('Current cash: MYR {0} (lastupdate {1})'.format(latestdata['cash']['value'], datetime.fromtimestamp(latestdata.index.values.astype(int)[0]).strftime('%Y-%m-%d %H:%M:%S')))
	else:
		currenttime = int(datetime.now().timestamp())
		initdb = {'cash': {'value': 0, 'add': False, 'remove': False, 'reset': True}, 'lastupdate': currenttime}
		cashdb = pd.DataFrame([initdb])
		cashdb.set_index(['lastupdate'], inplace=True)
		duitdb[user_id] = cashdb
		print(duitdb[user_id])
		#chat_data[user_id] = duitdb[user_id]
		pass

	print(chat_data.keys())


def manage(bot, update, chat_data):
	chat_id = update.message.chat_id
	try:
		update.message.reply_text(' - NO ITEM - ')
	except:
		update.message.reply_text(' - NO USER HISTORY - ')
		pass
	update.message.reply_text('manage')


def cash(bot, update, args, chat_data):
	keyboard = [[
		InlineKeyboardButton("Current Cash", callback_data='current'),
		InlineKeyboardButton("Add Cash", callback_data='add'),
		InlineKeyboardButton("Remove Cash", callback_data='remove'),
		InlineKeyboardButton("Reset Cash", callback_data="reset")
		]]
	reply_markup = InlineKeyboardMarkup(keyboard)
	update.message.reply_text("Reset Cash", reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)


def cashdecision(bot, update):
	query = update.callback_query
	chat_id = query.message.chat_id
	if 'add' in query.data:
		bot.edit_message_text(text="Add", chat_id=chat_id, message_id=query.message.message_id)
	elif 'current' in query.data:
		try:
			bot.edit_message_text(text="Current", chat_id=chat_id, message_id=query.message.message_id)
		except:
			pass
	elif 'remove' in query.data:
		bot.edit_message_text(text="Remove", chat_id=chat_id, message_id=query.message.message_id)
	elif 'reset' in query.data:
		bot.edit_message_text(text="Reset", chat_id=chat_id, message_id=query.message.message_id)
	else:
		bot.edit_message_text(text="Unexpected input", chat_id=chat_id, message_id=query.message.message_id)


def getprice(bot, update, args,chat_data):
	chat_id = update.message.chat_id
	if len(args) > 0:
		update.message.reply_text('Please wait. Fetching data...')
		for arg in args:
			bot.send_message(chat_id=chat_id, text="Data Collect",parse_mode=telegram.ParseMode.MARKDOWN)
			#bot.send_photo(chat_id=chat_id, photo=open("{0}.png".format(chat_id), 'rb'))


def notify(bot, job):
	try:
		bot.send_message(job.context, text="Summary", parse_mode=telegram.ParseMode.MARKDOWN)
	except:
		bot.send_message(job.context, text="Error")


def set_notify(bot, update, args, job_queue, chat_data):
	"""Add a job to the queue."""
	chat_id = update.message.chat_id
	try:
		due = int(args[0])
		if due < 0:
			update.message.reply_text('Sorry we can not go back to future!')
			return
		job = job_queue.run_repeating(notify, timedelta(minutes=due), context=chat_id)
		chat_data['job'] = job

		update.message.reply_text('Task successfully set with {0}min(s) interval!'.format(str(args[0])))

	except (IndexError, ValueError):
		update.message.reply_text('Usage: /set <minute>')


def unset(bot, update, chat_data):
	"""Remove the job if the user changed their mind."""
	if 'job' not in chat_data:
		update.message.reply_text('You have no active task')
		return

	job = chat_data['job']
	job.schedule_removal()
	del chat_data['job']

	update.message.reply_text('Task successfully removed!')


def help(bot, update):
	update.message.reply_text('~DuitTBot v{0}~ \n\n{1}')


def error(bot, update, error):
	"""Log Errors caused by Updates."""
	logger.warning('Update "%s" caused error "%s"', update, error)


def main():
	"""Run bot."""
	updater = Updater(token)

	# Get the dispatcher to register handlers
	dp = updater.dispatcher

	# on different commands - answer in Telegram
	'''
	spend
	'''
	dp.add_handler(CommandHandler("spend", spend, pass_args=True, pass_chat_data=True))
	dp.add_handler(CallbackQueryHandler(spenddecision))
	dp.add_handler(CommandHandler("getprice", getprice, pass_args=True, pass_chat_data=True))
	dp.add_handler(CommandHandler("manage", manage, pass_chat_data=True))
	'''
	cash
	'''
	dp.add_handler(CommandHandler("cash", cash, pass_args=True, pass_chat_data=True))
	dp.add_handler(CallbackQueryHandler(cashdecision))
	'''
	bank
	'''
	dp.add_handler(CommandHandler("bank",bank, pass_args=True,pass_chat_data=True))
	dp.add_handler(CallbackQueryHandler(bankdecision))
	'''
	etc
	'''
	dp.add_handler(CommandHandler("start", start, pass_chat_data=True))
	dp.add_handler(CommandHandler("help", help))
	dp.add_handler(CommandHandler("set", set_notify, pass_args=True, pass_job_queue=True, pass_chat_data=True))
	dp.add_handler(CommandHandler("unset", unset, pass_chat_data=True))

	# log all errors
	dp.add_error_handler(error)

	# Start the Bot
	updater.start_polling()

	# Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
	# SIGABRT. This should be used most of the time, since start_polling() is
	# non-blocking and will stop the bot gracefully.
	updater.idle()


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		duitdb.close()
		sys.exit()
