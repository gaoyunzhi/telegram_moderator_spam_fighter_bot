#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram_util import getDisplayUser, log_on_fail, TimedDeleter, tryDelete, splitCommand
import yaml
from db import shouldKick, kicklist, allowlist, addBlocklist, badText, shouldDelete

td = TimedDeleter()

with open('CREDENTIALS') as f:
    credentials = yaml.load(f, Loader=yaml.FullLoader)

updater = Updater(credentials['token'], use_context=True)
bot = updater.bot
debug_group = bot.get_chat(credentials['owner'])

def replyText(msg, text, timeout):
	try:
		return td.delete(msg.reply_text(text), timeout)
	except:
		pass

def kick(msg, member):
	try:
		for _ in range(2):
			bot.kick_chat_member(msg.chat.id, member.id)
	except:
		...

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	kicked = False
	for member in msg.new_chat_members:
		if shouldKick(member):
			tryDelete(msg)
			kick(msg, member)
			kicked = True
	if not kicked:
		td.delete(msg, 5)
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

def adminAction(msg, action):
	target = getAdminActionTarget(msg)
	if not target or not target.id:
		return
	target_id = str(target.id)

	kicklist.remove(target_id)
	allowlist.remove(target_id)
	if action == 'kick':
		kicklist.add(target_id)
	if action == 'allowlist':
		allowlist.add(target_id)

	if msg.chat_id != debug_group.id:
		if action == 'kick':
			msg.reply_to_message.delete()
		msg.chat.send_message('-').delete()
		msg.delete()
	debug_group.send_message(
		text=getDisplayUser(target) + ': ' + action, parse_mode='Markdown')

def isAdminMsg(msg):
	print(msg.from_user)
	if msg.from_user.id < 0:
		return True
	for admin in bot.get_chat_administrators(msg.chat_id):
		if admin.user.id == msg.from_user.id:
			return True
	return False

@log_on_fail(debug_group)
def handleGroupInternal(msg):
	if isAdminMsg(msg):
		return
	if shouldKick(msg.from_user):
		kick(msg, msg.from_user)
		tryDelete(msg)
		return

	timeout, reason = shouldDelete(msg)
	if timeout == float('Inf'):
		return

	if reason:
		replyText(msg, reason, 0.2)
	td.delete(msg, timeout)

def handleCommand(msg):
	command, text = splitCommand(msg.text)
	if not text:
		return
	if command in ['/abl', 'sb']:
		msg.chat.send_message(addBlocklist(text))
	if command in ['md', '/debug', '/md']:
		msg.chat.send_message('result: ' + str(badText(msg.text)))

def handleAdmin(msg):
	if msg.text in ['m', 'k']:
		adminAction(msg, 'kick')
	if msg.text in ['w']:  
		adminAction(msg, 'allowlist')
	if msg.text in ['r']:  
		adminAction(msg, 'reset')
	handleCommand(msg)

@log_on_fail(debug_group)
def handleGroup(update, context):
	msg = update.effective_message
	if not msg:
		return

	if msg.chat_id != debug_group.id:
		handleGroupInternal(msg)
	
	if msg.from_user.id == debug_group.id:
		handleAdmin(msg)

@log_on_fail(debug_group)
def handlePrivate(update, context):
	msg = update.message
	if msg.from_user.id == debug_group.id:
		handleAdmin(msg)
	else:
		msg.reply_text('Add me to groups and promote me as admin, I will do magic for you.')

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