#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram import ChatPermissions
from telegram_util import getDisplayUser, log_on_fail, autoDestroy
import yaml
from db import DB
from record_delete import recordDelete

unblock_requests = {}
chats = set()

with open('CREDENTIALS') as f:
    CREDENTIALS = yaml.load(f, Loader=yaml.FullLoader)

updater = Updater(CREDENTIALS['token'], use_context=True)
tele = updater.bot
debug_group = tele.get_chat(-1001198682178)
this_bot = tele.id
BOT_OWNER = CREDENTIALS['owner']
db = DB()

def replyText(msg, text, timeout):
	try:
		return autoDestroy(msg.reply_text(text), timeout)
	except Exception e:
		if str(e) != 'Reply message not found':
			raise e

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	kicked = False
	for member in msg.new_chat_members:
		if db.shouldKick(member):
			try:
				msg.delete()
				tele.kick_chat_member(msg.chat.id, member.id)
				kicked = True
			except:
				pass
	if not kicked:
		autoDestroy(msg, 5)
		replyText(msg, '欢迎新朋友！新朋友请自我介绍~', 5)

def getAdminActionTarget(msg):
	if not msg.reply_to_message:
		return
	for item in msg.reply_to_message.entities:
		if item['type'] == 'text_mention':
			return item.user
	if msg.chat_id != debug_group.id:
		return msg.reply_to_message.from_user
	return msg.reply_to_message.forward_from

def adminAction(db_action, msg, display_action):
	target = getAdminActionTarget(msg)
	if not target or not target.id:
		return
	db.record(db_action, target)
	if msg.chat_id != debug_group.id:
		if db_action == 'KICKLIST':
			msg.reply_to_message.delete()
		r = msg.reply_text('-')
		r.delete()
		msg.delete()
	debug_group.send_message(
		text=getDisplayUser(target) + ': ' + display_action,
		parse_mode='Markdown')

@log_on_fail(debug_group)
def handleAutoUnblock(usr = None, chat = None):
	global unblock_requests
	global chats
	p = ChatPermissions(
		can_send_messages=True, 
		can_send_media_messages=True, 
		can_send_polls=True, 
		can_add_web_page_previews=True)
	for u in (usr or unblock_requests.keys()):
		for c in (chat or chats):
			try:
				r = tele.restrict_chat_member(c, u, p)
			except:
				pass

def handleGroupInternal(msg):
	global chats
	if not msg.chat.id in chats:
		chats.add(msg.chat.id)
		handleAutoUnblock(chat = [msg.chat.id])
	if db.shouldKick(msg.from_user):
		tele.kick_chat_member(msg.chat.id, msg.from_user.id)
		msg.delete()
		return
	if db.replySender(msg):
		autoDestroy(msg)
		replyText(msg, db.replySender(msg), 1)
	if db.shouldDelete(msg):
		msg.delete()
	if db.shouldLog(msg):
		recordDelete(msg, debug_group, tele, db.getPermission(msg.from_user))

def handleAdmin(msg):
	# TODO: check do I need to mute anyone? Why not just kick them?
	if msg.text in ['mute', 'm']:
		adminAction('MUTELIST', msg, 'mute')
	if msg.text in ['kick', 'k']:
		adminAction('KICKLIST', msg, 'kick')
	if msg.text in ['white', 'w']:  
		adminAction('WHITELIST', msg, 'whitelist')
	if msg.text in ['reset', 'r']:  
		adminAction(None, msg, 'reset')

@log_on_fail(debug_group)
def handleGroup(update, context):
	msg = update.effective_message
	if not msg:
		return

	if msg.chat_id != debug_group.id:
		handleGroupInternal(msg)

	if msg.from_user.id == BOT_OWNER:
		handleAdmin(msg)

@log_on_fail(debug_group)
def handlePrivate(update, context):
	global unblock_requests
	update.message.reply_text(
		'''For group owner, Add me to groups and promote me as admin, I will do magic for you. 

For group member requesting unblock, your request has recieved.''')
	usr = update.effective_user
	if usr.id not in unblock_requests:
		unblock_requests[usr.id] = usr
		handleAutoUnblock(usr = [usr.id])

def deleteMsgHandle(update, context):
	update.message.delete()

dp = updater.dispatcher
dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, handleJoin), group=1)
dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, deleteMsgHandle), group = 2)
dp.add_handler(MessageHandler(Filters.group & \
		(~ Filters.status_update.left_chat_member) & \
		(~ Filters.status_update.new_chat_members), handleGroup), group = 3)
dp.add_handler(MessageHandler(Filters.private, handlePrivate), group = 4)

updater.start_polling()
updater.idle()