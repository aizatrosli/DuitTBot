#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, io
from msg import *
from datetime import datetime,timedelta
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging,telegram
from datagrab import *
import matplotlib.pyplot as plt
import six
import pandas as pd
import numpy as np

'''VARS'''
USERDB = pd.HDFStore('userdb.h5')
ITEMDB = pd.HDFStore('itemdb.h5')
DICTITEMS = {}
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

def itemlist(bot, update,chat_data):
	if not chat_data['DICTITEMS']:
		chat_data['DICTITEMS'] = getallitemlist()
	message = ["[{0}] {1}".format(key,val) for key, val in chat_data['DICTITEMS'].items()]
	msgs = [message[i:i + 10] for i in range(0, len(message), 10)]
	for text in msgs:
		update.message.reply_text(text="\n".join(text))

def finditemlist(bot, update, args, chat_data):
	if not chat_data['DICTITEMS']:
		chat_data['DICTITEMS'] = getallitemlist()
	newmessage = []
	if len(args[0]) > 0:
		message = ["[{0}] {1}".format(key,val) for key, val in chat_data['DICTITEMS'].items()]
		for text in message:
			if str(args[0]) in text:
				newmessage.append(text)
	msgs = [newmessage[i:i + 10] for i in range(0, len(newmessage), 10)]
	for text in msgs:
		update.message.reply_text(text="\n".join(text))

def start(bot, update, chat_data):
	update.message.reply_text('{0}\n\nUse {1}\nUse {2}\nUse {3}'.format(SPLASHSTR,HELP['GETPRICE'],HELP['ITEMLIST'],HELP['HELP']))
	chat_data['DICTITEMS'] = getallitemlist()

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

def addlist(bot, update, args, chat_data):
	chat_id = update.message.chat_id
	if 'DICTITEMS' in chat_data.keys():
		chat_data['DICTITEMS'] = getallitemlist()
	itemarr = []
	try:
		itemarr = USERDB[str(chat_id)][0].tolist()
	except:
		itemarr = []
		pass
	if len(args) > 0:
		for arg in args:
			argstr = chat_data['DICTITEMS'][int(arg)] if arg.isdigit() else arg
			itemarr.append(argstr)
	USERDB[str(chat_id)] = pd.DataFrame(list(set(itemarr)))
	update.message.reply_text("{0} Use {1}".format(ACTION['ADDLIST'],HELP['MANAGE']))

def clearlist(bot, update):
	keyboard = [[InlineKeyboardButton("YES", callback_data='Yes'),
				InlineKeyboardButton("NO", callback_data='No')]]
	reply_markup = InlineKeyboardMarkup(keyboard)
	update.message.reply_text(ACTION['CLEARLIST'], reply_markup=reply_markup,parse_mode=telegram.ParseMode.MARKDOWN)

def clearlistdecision(bot, update):
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
		itemarr = USERDB[str(job.context)][0].tolist()
		for item in itemarr:
			pricedf = getlatestpriceitem(item)
			drawtable(pricedf).savefig("{0}.png".format(job.context), bbox_inches='tight')
			bot.send_message(job.context, text="*[{0}]* {1}Zeny".format(item,pricedf['price'][0]),parse_mode=telegram.ParseMode.MARKDOWN)
			bot.send_photo(job.context, photo=open("{0}.png".format(job.context), 'rb'))
	except:
		bot.send_message(job.context, text="ERROR!!.\nUse {0}\n{1}".format(HELP['ADDLIST'],ERROR['NOTIFY']))

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
    update.message.reply_text('~PoPoBot v{0}~ \n\n{1}'.format(getversion(),HELPSTR))

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def drawtable(data, col_width=3.0, row_height=0.625, font_size=14,
                     header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0,
                     ax=None, **kwargs):
    if ax is None:
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size)
        ax.axis('off')

    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    for k, cell in  six.iteritems(mpl_table._cells):
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
    return fig

def main():
    """Run bot."""
    updater = Updater()

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start,pass_chat_data=True))
    dp.add_handler(CommandHandler("getprice", getprice, pass_args=True,pass_chat_data=True))
    dp.add_handler(CommandHandler("itemlist", itemlist,pass_chat_data=True))
    dp.add_handler(CommandHandler("manage",manage))
    dp.add_handler(CommandHandler("clearlist",clearlist))
    dp.add_handler(CallbackQueryHandler(clearlistdecision))
    dp.add_handler(CommandHandler("addlist",addlist, pass_args=True,pass_chat_data=True))
    dp.add_handler(CommandHandler("finditemlist",finditemlist, pass_args=True,pass_chat_data=True))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("set", set_notify,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
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
		USERDB.close()
		ITEMDB.close()
		sys.exit()
