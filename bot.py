#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, io
from datetime import datetime, timedelta
from base import *
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging, telegram
import pandas as pd
import numpy as np


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)
cashdb = pd.HDFStore('cash.h5')
bankdb = pd.HDFStore('bank.h5')


def cash(bot, update, args, chat_data):
	if not chat_data['DICTITEMS']:
		chat_data['DICTITEMS'] = getallitemlist()
	newmessage = []
	'''workaround for longlist'''''
	if len(args[0]) > 0:
		message = ["[{0}] {1}".format(key,val) for key, val in chat_data['DICTITEMS'].items()]
		for text in message:
			if str(args[0]) in text:
				newmessage.append(text)
	msgs = [newmessage[i:i + 10] for i in range(0, len(newmessage), 10)]
	for text in msgs:
		update.message.reply_text(text="\n".join(text))


def start(bot, update, chat_data):
	update.message.reply_text('DuitTBot')
	print(chat_data.keys())


def manage(bot, update):
	chat_id = update.message.chat_id
	try:
		if len(USERDB[str(chat_id)][0].tolist()) > 0:
			update.message.reply_text('\n'.join(USERDB[str(chat_id)][0].tolist()))
		else:
			update.message.reply_text(' - NO ITEM - ')
	except:
		update.message.reply_text(' - NO USER HISTORY - ')
		pass
	update.message.reply_text('Use {0}\nUse {1}'.format(HELP['ADDLIST'],HELP['ITEMLIST']))


def cash(bot, update, chat_data):
	update.message.reply_text('Current cash')


def addcash(bot, update, args, chat_data):
	chat_id = update.message.chat_id
	currentcash = 0
	try:
		currentcash = cashdb['current']
	except KeyError:
		pass
	if len(args[0]) > 0:
		currentcash = currentcash + float(args[0])
		cashdb['current'] = currentcash
	update.message.reply_text("Cash : {0}".format(currentcash))


def resetcash(bot, update):
	keyboard = [[InlineKeyboardButton("YES", callback_data='Yes'),
				InlineKeyboardButton("NO", callback_data='No')]]
	reply_markup = InlineKeyboardMarkup(keyboard)
	update.message.reply_text("Reset Cash", reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)


def resetcashdecision(bot, update):
	query = update.callback_query
	chat_id = query.message.chat_id
	if 'Yes' in query.data:
		USERDB[str(chat_id)] = pd.DataFrame()
		bot.edit_message_text(text=ACTION['CLEARLISTY'],chat_id=chat_id, message_id=query.message.message_id)
	else:
		bot.edit_message_text(text=ACTION['CLEARLISTN'],chat_id=chat_id, message_id=query.message.message_id)


def getprice(bot, update, args,chat_data):
	chat_id = update.message.chat_id
	if len(args) > 0:
		update.message.reply_text('Please wait. Fetching data...')
		for arg in args:
			argstr = chat_data['DICTITEMS'][int(arg)] if arg.isdigit() else arg
			pricedf = getlatestpriceitem(argstr)
			drawtable(pricedf).savefig("{0}.png".format(chat_id), bbox_inches='tight')
			bot.send_message(chat_id=chat_id, text="*[{0}]* {1}Zeny\n".format(argstr,pricedf['price'][0]),parse_mode=telegram.ParseMode.MARKDOWN)
			bot.send_photo(chat_id=chat_id, photo=open("{0}.png".format(chat_id), 'rb'))


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
	updater = Updater()

	# Get the dispatcher to register handlers
	dp = updater.dispatcher

	# on different commands - answer in Telegram
	'''
	spend
	'''
	dp.add_handler(CommandHandler("getprice", getprice, pass_args=True, pass_chat_data=True))
	dp.add_handler(CommandHandler("manage", manage))
	'''
	cash
	'''
	dp.add_handler(CommandHandler("cash", cash, pass_chat_data=True))
	dp.add_handler(CommandHandler("addcash", addcash, pass_args=True, pass_chat_data=True))
	dp.add_handler(CommandHandler("emptycash", resetcash))
	dp.add_handler(CallbackQueryHandler(resetcashdecision))
	'''
	bank
	'''
	dp.add_handler(CommandHandler("bank",bank, pass_args=True,pass_chat_data=True))
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
		cashdb.close()
		bankdb.close()
		sys.exit()
