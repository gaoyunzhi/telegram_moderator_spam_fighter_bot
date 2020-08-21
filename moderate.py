#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from botgram.ext import Updater, MessageHandler, Filters
from botgram import ChatPermissions
from botgram_util import getDisplayUser, log_on_fail, TimedDeleter, matchKey, tryDelete
import yaml
from db import shouldKick

unblock_requests = {}
chats = set()
td = TimedDeleter()

with open('CREDENTIALS') as f:
    credentials = yaml.load(f, Loader=yaml.FullLoader)

updater = Updater(credentials['token'], use_context=True)
bot = updater.bot
bot_owner = credentials['owner']
debug_group = bot.get_chat(bot_owner)
db = DB()
gs = GroupSetting()

def replyText(msg, text, timeout):
	try:
		return td.delete(msg.reply_text(text), timeout)
	except:
		pass

def kick(msg, member):
	try:
		for _ in range(2):
			bot.kick_chat_member(msg.chat.id, member.id)
	except Exception as e:
		...

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	kicked = False
	for member in msg.new_chat_members:
		if shouldKick(member):
			tryDelete(msg)
			kicked = True
			kick(msg, member)
	if not kicked:
		td.delete(msg, 5)
		greeting = gs.getGreeting(msg.chat_id)
		if greeting:
			replyText(msg, greeting, 5)

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
	record(db_action, target)
	if msg.chat_id != debug_group.id:
		if db_action == 'KICKLIST':
			msg.reply_to_message.delete()
		r = msg.chat.send_message('-')
		r.delete()
		msg.delete()
	debug_group.send_message(
		text=getDisplayUser(target) + ': ' + display_action,
		parse_mode='Markdown')

def isAdminMsg(msg):
	for admin in bot.get_chat_administrators(msg.chat_id):
		if admin.user.id == msg.from_user.id and (admin.can_delete_messages or not admin.can_be_edited):
			return True
	return False

def containBotOwnerAsAdmin(msg):
	for admin in bot.get_chat_administrators(msg.chat_id):
		if admin.user.id == bot_owner:
			return True
	return False

@log_on_fail(debug_group)
def handleGroupInternal(msg):
	if shouldKick(msg.from_user):
		kick(msg, msg.from_user)
		td.delete(msg, 0)
		return
	if isAdminMsg(msg):
		return

	timeout, reason = shouldDelete(msg)
	if timeout != float('Inf'):
		if reason:
			replyText(msg, reason, 1)
		td.delete(msg, timeout)

def handleCommand(msg):
	if not msg.text or len(msg.text.split()) < 2:
		return
	command = msg.text.split()[0].lower()
	text = msg.text.split()[1]
	if not text:
		return
	if command in ['/abl', 'sb']:
		r = setBadness(text, float(msg.text.split()[2]))
		msg.chat.send_message(r)
	if command in ['md', '/debug', '/md']:
		r = badText(msg.text)
		msg.chat.send_message('result: ' + str(r))

def handleAdmin(msg):
	if msg.text in ['m', 'k']:
		adminAction('KICKLIST', msg, 'kick')
	if msg.text in ['w']:  
		adminAction('WHITELIST', msg, 'whitelist')
	if msg.text in ['r']:  
		adminAction(None, msg, 'reset')
	handleCommand(msg)

@log_on_fail(debug_group)
def handleGroup(update, context):
	msg = update.effective_message
	if not msg:
		return

	if msg.chat_id != debug_group.id and \
		not gs.isModerationDisabled(msg.chat_id):
		handleGroupInternal(msg)

	if msg.text and msg.text.startswith('/m') and isAdminMsg(msg):
		handleWildAdmin(msg)

	if msg.from_user.id == bot_owner:
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