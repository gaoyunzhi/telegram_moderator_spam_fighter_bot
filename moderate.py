#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram_util import getDisplayUserHtml, log_on_fail, TimedDeleter, tryDelete, splitCommand
from db import shouldKick, kicklist, allowlist, addBlocklist, badText, shouldDelete
import time

td = TimedDeleter()

with open('token') as f:
    updater = Updater(f.read().strip(), use_context=True)

bot = updater.bot
debug_group = bot.get_chat(-1001263616539)

recent_logs = []

class LogInfo(object):
	def __init__(self):
		self.id = 0
		self.size = 0
		self.text = ''
		self.user = ''
		self.chat = ''
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

def getAdminActionTargets(msg):
	if not msg.reply_to_message:
		return {}
	result = {}
	for item in msg.reply_to_message.entities:
		if item['type'] == 'text_mention':
			result[item.user.id] = item.user
	try:
		for uid in msg.reply_to_message.text.split(',')[0].split()[1:]:
			uid = int(uid)
			if uid not in result:
				result[uid] = None
	except:
		...
	return result

def adminAction(msg, action):
	targets = getAdminActionTargets(msg)
	if not targets:
		return
	for target_id in targets:
		kicklist.remove(target_id)
		allowlist.remove(target_id)
		if action == 'kick':
			kicklist.add(target_id)
		if action == 'allowlist':
			allowlist.add(target_id)

	display_user = [getDisplayUserHtml(targets[uid]) if targets[uid] else str(uid) for uid in targets]
	msg.edit_text(text=' '.join(display_user) + ': ' + action, parse_mode='HTML')
	
def isAdminMsg(msg):
	if msg.from_user.id < 0:
		return True
	for admin in bot.get_chat_administrators(msg.chat_id):
		if admin.user.id == msg.from_user.id:
			return True
	return False

def getRawLogInfo(msg):
	info = LogInfo()
	info.id = msg.from_user.id
	info.user = getDisplayUserHtml(msg.from_user)
	info.chat = '<a href="%s">%s</a>' % (msg.link, msg.chat.title)
	info.text = msg.caption_html or msg.text_html or ''
	if msg.photo:
		info.size = msg.photo[-1].file_size
	if msg.video:
		info.size = msg.video.file_size
	if msg.document:
		info.size = msg.document.file_size
	return info

def isSimilarLog(log1, log2):
	if log1.size == log2.size and log2.size > 10:
		print('log1.size', log1.size)
		return True
	if log1.text == log2.text and len(log2.text) > 10:
		return True
	return False

def getSimilarLogs(log_info):
	global recent_logs
	recent_logs = [recent_log for recent_log in recent_logs if recent_log[1] > time.time() - 60 * 60]
	other_ids = set()
	other_users = set()
	other_chats = set()
	for recent_log_info, timestemp, old_logs in recent_logs:
		if not isSimilarLog(recent_log_info, log_info):
			continue
		for old_log in old_logs:
			other_ids.add(recent_log_info.id)
			other_users.add(recent_log_info.user)
			other_chats.add(recent_log_info.chat)
			try:
				old_log.delete()
			except:
				...
	other_ids.discard(log_info.id)
	other_users.discard(log_info.user)
	other_chats.discard(log_info.chat)
	return other_ids, other_users, other_chats

def getDisplayLogInfo(log_info, other_logs):
	ids = [log_info.id] + list(other_logs[0])
	users = [log_info.user] + list(other_logs[1])
	chats = [log_info.chat] + list(other_logs[2])
	display = 'id: %s, user: %s, chat: %s' % (
		' '.join([str(uid) for uid in ids]), ' '.join(users), ' '.join(chats))
	if log_info.kicked:
		display += ', kicked'
	if log_info.delete == 0:
		display += ', deleted'
	elif log_info.delete != float('Inf'):
		display += ', scheduled delete in %d minute' % log_info.delete
	return display

@log_on_fail(debug_group)
def log(log_info, msg, logs):
	similar_logs = getSimilarLogs(log_info)
	logs.append(debug_group.send_message(getDisplayLogInfo(log_info, similar_logs),
		parse_mode='HTML', disable_web_page_preview=True))
	recent_logs.append((log_info, time.time(), logs))

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
	logs = []
	try:
		logs.append(msg.forward(debug_group.id))
	except:
		...
	log(handleGroupInternal(msg), msg, logs)
	
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