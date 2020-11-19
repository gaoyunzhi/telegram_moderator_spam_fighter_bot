#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram_util import getDisplayUserHtml, getDisplayChatHtml, log_on_fail, TimedDeleter, tryDelete, splitCommand
from db import shouldKick, kicklist, allowlist, addBlocklist, badText, shouldDelete, forward_block

td = TimedDeleter()

with open('token') as f:
    updater = Updater(f.read().strip(), use_context=True)

bot = updater.bot
debug_group = bot.get_chat(-1001263616539)

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

def getBlockKeys(msg):
	if not msg:
		return []
	to_block = []
	forward_channel = msg.forward_from_chat
	if forward_channel:
		to_block.append(forward_channel.id)
		to_block.append(forward_channel.title)
		to_block.append(forward_channel.username)
	for photo in (msg.photo or []):
		to_block.append(photo.file_unique_id)
	to_block.append(msg.video and msg.video.file_unique_id)
	return [str(item) for item in to_block if item]

def forwardBlock(msg):
	orig_msg = msg.reply_to_message
	keys = getBlockKeys(orig_msg)
	for key in keys:
		forward_block.add(key)
	msg.edit_text('blocked forward keys: ' + ' '.join(keys))
	
def isAdminMsg(msg):
	if msg.from_user.id < 0:
		return True
	for admin in bot.get_chat_administrators(msg.chat_id):
		if admin.user.id == msg.from_user.id:
			return True
	return False

def shouldSkipOrigLog(msg):
	return set(getBlockKeys(msg)) & set(forward_block.items())

@log_on_fail(debug_group)
def log(msg):
	should_skip_orig_log = shouldSkipOrigLog(msg)
	if should_skip_orig_log:
		tail = (', msg known bad, skip log: ' + ' '.join(should_skip_orig_log) + 
			', cap: ' + (msg.caption or msg.text or 'None')[:50])
	else:
		tail = ''
		try:
			msg.forward(debug_group.id)
		except:
			...
	return debug_group.send_message('id: %d, user: %s, chat: %s, link: %s%s' % (
		msg.from_user.id, getDisplayUserHtml(msg.from_user),
		getDisplayChatHtml(msg.chat), msg.link or '', tail), 
		parse_mode='HTML', disable_web_page_preview=True)

@log_on_fail(debug_group)
def handleGroupInternal(msg):
	if msg.from_user.id in [777000, 420074357, 1088415958, 1066746613]: # telegram channel auto forward, owner, 文学部, moth lib
		return
	# see if we need a manual sleep to slow down the message flow
	debug_log = log(msg)
	if isAdminMsg(msg):
		return
	if shouldKick(msg.from_user):
		kick(msg, msg.from_user)
		tryDelete(msg)
		debug_log.edit_text(debug_log.text_html + ', from user known to be bad, user kicked, message deleted.',
			parse_mode='HTML', disable_web_page_preview=True)
		return

	timeout = shouldDelete(msg)
	if timeout == float('Inf'):
		return
	replyText(msg, '非常抱歉，本群不支持转发与多媒体信息，我们将在%d分钟后自动删除您的消息。' % int(timeout + 1), 0.2)
	td.delete(msg, timeout)
	debug_log.edit_text(debug_log.text_html + ', scheduled delete in %d minute' % int(timeout),
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
	if msg.text in ['b']:
		forwardBlock(msg)
	handleCommand(msg)

@log_on_fail(debug_group)
def handleGroup(update, context):
	msg = update.effective_message
	if not msg:
		return
	handleGroupInternal(msg)

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