#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram_util import getDisplayUserHtml, log_on_fail, TimedDeleter, tryDelete, splitCommand
from db import shouldKick, kicklist, allowlist, addBlocklist, badText, shouldDelete

td = TimedDeleter()

with open('token') as f:
    updater = Updater(f.read().strip(), use_context=True)

bot = updater.bot
debug_group = bot.get_chat(-1001263616539)

class LogInfo(object):
	def __init__(self):
		self.id = 0
		self.size = 0
		self.text = ''
		self.user = ''
		self.chat = ''
		self.text = 'None'
		self.kicked = False
		self.delete = float('Inf')

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
			return item.user.id, item.user
	return int(msg.reply_to_message.text.split()[1][:-1]), None

def adminAction(msg, action):
	target_id, target = getAdminActionTarget(msg)
	if not target_id:
		return
	kicklist.remove(target_id)
	allowlist.remove(target_id)
	if action == 'kick':
		kicklist.add(target_id)
	if action == 'allowlist':
		allowlist.add(target_id)

	display_user = getDisplayUserHtml(target) if target else str(target_id)

	msg.edit_text(
		text=display_user + ': ' + action, parse_mode='HTML')
	
def isAdminMsg(msg):
	if msg.from_user.id < 0:
		return True
	for admin in bot.get_chat_administrators(msg.chat_id):
		if admin.user.id == msg.from_user.id:
			return True
	return False

def getRawLogInfo(msg):
	info = LogInfo()
	info.id = msg.from_user.id,
	info.user = getDisplayUserHtml(msg.from_user),
	info.chat = '<a href="%s">%s</a>' % (msg.link, msg.chat.title)
	info.text = msg.caption_html or msg.text_html or 'None'
	if msg.photo:
		info.size = msg.photo[-1].file_size
	if msg.video:
		info.size = msg.video.file_size
	if msg.document:
		info.size = msg.document.file_size
	return info

@log_on_fail(debug_group)
def log(log_info):
	# let's see if logs can be combined
	if msg:
		try:
			msg.forward(debug_group.id)
		except:
			...
	debug_group.send_message('\n'.join([key + ': ' + str(value) for key, value in log_info.items()])
		parse_mode='HTML', disable_web_page_preview=True)

def handleCommand(msg):
	command, text = splitCommand(msg.text)
	if not text:
		return
	if command in ['/abl', 'sb']:
		msg.chat.send_message(addBlocklist(text))
	if command in ['md', '/debug', '/md']:
		msg.chat.send_message('result: ' + str(badText(msg.text)))

@log_on_fail(debug_group)
def handleAdmin(update, context):
	msg = update.effective_message
	if not msg or msg.chat.id != debug_group.id:
		return
	if msg.text in ['m', 'k']:
		adminAction(msg, 'kick')
	if msg.text in ['w']:  
		adminAction(msg, 'allowlist')
	if msg.text in ['r']:  
		adminAction(msg, 'reset')
	handleCommand(msg)

def handleGroupInternal(msg):
	log_info = getRawLogInfo(msg)
	if isAdminMsg(msg):
		return log_info
	if shouldKick(msg.from_user):
		kick(msg, msg.from_user)
		tryDelete(msg)
		log_info.kicked = True
		return log_info
	timeout = shouldDelete(msg)
	if timeout == float('Inf'):
		return log_info
	replyText(msg, '非常抱歉，本群不支持转发与多媒体信息，我们将在%d分钟后自动删除您的消息。' % int(timeout + 1), 0.2)
	td.delete(msg, timeout)
	log_info.delete = int(timeout)
	return log_info

@log_on_fail(debug_group)
def handleGroup(update, context):
	msg = update.effective_message
	if not msg:
		return
	if msg.from_user.id in [777000, 420074357, 1087968824, 1088415958, 1066746613]: # telegram channel auto forward, owner, group anonymous bot, 文学部, moth lib
		return
	log(handleGroupInternal(msg))
	
def deleteMsgHandle(update, context):
	update.message.delete()

dp = updater.dispatcher
dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, handleJoin), group=1)
dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, deleteMsgHandle), group = 2)
dp.add_handler(MessageHandler(Filters.group & \
		(~ Filters.status_update.left_chat_member) & \
		(~ Filters.status_update.new_chat_members), handleGroup), group = 3)
dp.add_handler(MessageHandler(Filters.update.channel_posts, handleAdmin), group = 4)

updater.start_polling()
updater.idle()