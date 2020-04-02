#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram import ChatPermissions
from telegram_util import getDisplayUser, log_on_fail, autoDestroy, matchKey
import yaml
from db import DB, GroupSetting
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
gs = GroupSetting()

def replyText(msg, text, timeout):
	try:
		return autoDestroy(msg.reply_text(text), timeout)
	except Exception as e:
		if str(e) != 'Reply message not found':
			raise e

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	kicked = False
	for member in msg.new_chat_members:
		if db.shouldKick(member):
			autoDestroy(msg, 0)
			kicked = True
			try:
				tele.kick_chat_member(msg.chat.id, member.id)
			except:
				pass
	if not kicked:
		autoDestroy(msg, 5)
		replyText(msg, gs.getGreeting(msg.chat_id), 5)

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

def isAdminMsg(msg):
	for admin in tele.get_chat_administrators(msg.chat_id):
		if admin.user.id == msg.from_user.id and (admin.can_delete_messages or not admin.can_be_edited):
			return True
	return False

@log_on_fail(debug_group)
def handleGroupInternal(msg):
	global chats
	if not msg.chat.id in chats:
		chats.add(msg.chat.id)
		handleAutoUnblock(chat = [msg.chat.id])
	if db.shouldKick(msg.from_user):
		tele.kick_chat_member(msg.chat.id, msg.from_user.id)
		autoDestroy(msg, 0)
		return
	if isAdminMsg(msg):
		return

	external_reason = db.replySender(msg)
	if external_reason:
		replyText(msg, external_reason, 1)
		autoDestroy(msg)

	internal_reason = db.shouldDelete(msg)
	if internal_reason:
		if internal_reason != True:
			replyText(msg, internal_reason, 0)
		autoDestroy(msg, 0)

	log_reason = db.shouldLog(msg)
	if log_reason:
		recordDelete(msg, debug_group, tele, 
			db.getPermission(msg.from_user), log_reason)

def handleCommand(msg):
	if not msg.text or not len(msg.text.split()) == 2:
		return
	command = msg.text.split()[0].lower()
	text = msg.text.split()[1]
	if not text:
		return
	if command in ['rb', 'reducebadness']:
		r = db.reduceBadness(text)
		msg.chat.send_message(r)
	if command in ['ab', 'addbadness']:
		r = db.addBadness(text)
		msg.chat.send_message(r)

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
	handleCommand(msg)

def handleWildAdminInternal(msg):
	if matchKey(msg.text, ['enable_moderation', 'em']):
		print(2)
		gs.setDisableModeration(msg.chat_id, False)
		return 'moderation enabled'
	if matchKey(msg.text, ['disable_moderation', 'dm']):
		gs.setDisableModeration(msg.chat_id, True)
		return 'moderation disabled'
	if matchKey(msg.text, ['set_greeting', 'sg']):
		if msg.text.find(' ') != -1:
			greeting = msg.text[msg.text.find(' '):].strip()
		else:
			greeting = ''
		gs.setGreeting(msg.chat_id, greeting)
		return 'greeting set to: ' + greeting

def handleWildAdmin(msg):
	r = handleWildAdminInternal(msg)
	if r:
		autoDestroy(msg.reply_text(r), 0.1)
		msg.delete()

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