#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram import ChatPermissions
import time
import os
import traceback as tb
from telegram_util import getDisplayUser, log_on_fail, getTmpFile, autoDestroy, matchKey
import yaml

unblock_requests = {}
chats = set()
JOIN_TIME = {}
NEW_USER_WAIT_TIME = 3600 * 24 * 3

with open('CREDENTIALS') as f:
    CREDENTIALS = yaml.load(f, Loader=yaml.FullLoader)

updater = Updater(CREDENTIALS['token'], use_context=True)
tele = updater.bot
debug_group = tele.get_chat(-1001198682178)
this_bot = tele.id
BOT_OWNER = CREDENTIALS['owner']

quotes = ["'", '"', '‘', '“', '【']

with open('BETTER_AVOID_WORDS') as f:
    better_avoid_words = set(yaml.load(f, Loader=yaml.FullLoader))

with open('BLACKLIST') as f:
	BLACKLIST = [x.strip() for x in f.readlines()]
	BLACKLIST = set([x for x in BLACKLIST if x])

try:
	with open('WHITELIST') as f:
		WHITELIST = [x.strip() for x in f.readlines()]
		WHITELIST = set([x for x in WHITELIST if x])
except:
	WHITELIST = set()

with open('KICK_KEYS') as f:
    KICK_KEYS = set(yaml.load(f, Loader=yaml.FullLoader))

def saveList():
	with open('BLACKLIST', 'w') as f:
		f.write('\n'.join(sorted(BLACKLIST)))
	with open('WHITELIST', 'w') as f:
		f.write('\n'.join(sorted(WHITELIST)))

def needKick(user):
	name = getDisplayUser(user)
	return matchKey(name.lower(), KICK_KEYS)

def highRiskUsr(user):
	name = getDisplayUser(user).lower()
	try:
		int(user.first_name)
		return True
	except:
		pass
	for index, x in enumerate(name):
		if name[index:index + 3] == x * 3:
			return True
	if not user.last_name and not user.username:
		return True
	return matchKey(name, BLACKLIST)

def ban(bad_user, mute=False):
	if bad_user.id in [this_bot, BOT_OWNER]:
		return  # don't ban the bot itself :p
	if str(bad_user.id) in BLACKLIST and not mute:
		debug_group.send_message(
			text=getDisplayUser(bad_user) + ' already banned',
			parse_mode='Markdown')
		return
	BLACKLIST.add(str(bad_user.id))
	saveList()
	debug_group.send_message(
		text=getDisplayUser(bad_user) + ' banned',
		parse_mode='Markdown')

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	try:
		msg.delete()
	except:
		pass
	for member in msg.new_chat_members:
		if member.id == this_bot:
			continue
		if needKick(member):
			context.bot.kick_chat_member(msg.chat.id, member.id)
			ban(member, True)
			debug_group.send_message(
				getDisplayUser(member) + ' kicked from ' + getGroupName(msg.chat),
				parse_mode='Markdown',
				disable_web_page_preview=True)
			continue
		if highRiskUsr(member):
			ban(member, True)
			continue
		debug_group.send_message(
			getDisplayUser(member) + ' joined ' + getGroupName(msg.chat),
			parse_mode='Markdown',
			disable_web_page_preview=True)
		JOIN_TIME[msg.chat.id] = JOIN_TIME.get(msg.chat.id, {})
		JOIN_TIME[msg.chat.id][member.id] = time.time()

def isNewUser(msg):
	if not msg.chat.id in JOIN_TIME:
		return False
	if not msg.from_user.id in JOIN_TIME[msg.chat.id]:
		return False
	return JOIN_TIME[msg.chat.id][
			msg.from_user.id] > time.time() - NEW_USER_WAIT_TIME

def isMultiMedia(msg):
	return msg.photo or msg.sticker or msg.video

def badText(text):
	return matchKey(text, KICK_KEYS) or matchKey(text, BLACKLIST)

def containRiskyWord(msg):
	if badText(getDisplayUser(msg.from_user)):
		return True
	if msg.forward_from:
		if badText(getDisplayUser(msg.forward_from)):
			return True
	if badText(msg.text):
		return True
	return False

def shouldDelete(msg):
	usr = str(msg.from_user.id)
	if usr in BLACKLIST:
		return True
	if usr in WHITELIST:
		return False
	if containRiskyWord(msg):
		return True
	if isNewUser(msg) and isMultiMedia(msg):
		return True
	return False

def getGroupName(chat):
	if chat.username:
		link = 't.me/' + chat.username 
	else:
		try:
			link = tele.export_chat_invite_link(chat.id)
		except:
			link = ''
	return '[%s](%s)' % (chat.title, link)

def getMsgType(msg):
	if msg.photo:
		return 'sent photo in'
	if msg.video:
		return 'sent video in'
	if msg.sticker:
		return 'sent sticker in'
	if msg.text:
		return 'texted'
	if msg.left_chat_member:
		return 'left'
	if msg.new_chat_members:
		return 'joined'
	return 'did some action'

def getActionUsers(msg):
	if msg.new_chat_members:
		return msg.new_chat_members
	if msg.left_chat_member:
		return [msg.left_chat_member]
	return [msg.from_user]

@log_on_fail(debug_group)
def deleteMsg(msg):
	action_users = getActionUsers(msg)
	names = ', '.join([getDisplayUser(x) for x in action_users])
	debug_group.send_message(
		text=names + ' ' + getMsgType(msg) + 
		' ' + getGroupName(msg.chat),
		parse_mode='Markdown',
		disable_web_page_preview=True)
	try:
		msg.forward(debug_group.id)
	except:
		pass
	try:
		msg.delete()
	except:
		pass

def unban(not_so_bad_user, mute=False):
	if not_so_bad_user.id not in WHITELIST:
		WHITELIST.add(str(not_so_bad_user.id))
		saveList()
		debug_group.send_message(
			text=getDisplayUser(not_so_bad_user) + ' new user whitelisted.',
			parse_mode='Markdown')
	elif not mute:
		debug_group.send_message(
			text=getDisplayUser(not_so_bad_user) + ' already whitelisted.',
			parse_mode='Markdown')
	if str(not_so_bad_user.id) not in BLACKLIST:
		if not mute:
			debug_group.send_message(
				text=getDisplayUser(not_so_bad_user) + ' not banned',
				parse_mode='Markdown')
		return
	BLACKLIST.remove(str(not_so_bad_user.id))
	saveList()
	debug_group.send_message(
		text=getDisplayUser(not_so_bad_user) + ' unbanned',
		parse_mode='Markdown')

def markAction(msg, action, mute=False):
	if not msg.reply_to_message:
		return
	for item in msg.reply_to_message.entities:
		if item['type'] == 'text_mention':
			action(item.user, mute)
			return
	if msg.chat_id != debug_group.id:
		action(msg.reply_to_message.from_user, mute)
		r = msg.reply_text('请大家互相理解，友好交流。')
		r.delete()
		try:
			msg.delete()
		except:
			pass
	else:
		action(msg.reply_to_message.forward_from, mute)

@log_on_fail(debug_group)
def remindIfNecessary(msg):
	if not msg.text:
		return
	if matchKey(msg.text, better_avoid_words) and not matchKey(msg.text, quotes):
		reminder = '建议避免使用带有强烈主观判断的词哦，比如：' + ', '.join(better_avoid_words) + \
			'。 谢谢啦！'
		autoDestroy(msg.reply_text(reminder), 10)
	emotional_words = ['意淫', '凭什么']
	if matchKey(msg.text, emotional_words):
		reminder = '反问，反讽不利于友好交流哦，建议您换成大家更容易理解的表达哦。谢谢啦！'
		autoDestroy(msg.reply_text(reminder), 10)
	attacking_words = ['太low']
	if matchKey(msg.text, attacking_words):
		reminder = '请友好交流，争取互相理解。谢谢啦！'
		autoDestroy(msg.reply_text(reminder), 10)

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
				print(r)
				if r:
					debug_group.send_message(
						text=getDisplayUser(unblock_requests[u]) + 
							' auto unblocked in ' + getGroupName(tele.get_chat(c)),
						parse_mode='Markdown',
						disable_web_page_preview=True)
			except:
				pass

@log_on_fail(debug_group)
def handleGroup(update, context):
	global chats
	msg = update.effective_message
	if not msg:
		return
	if not msg.chat.id in chats:
		chats.add(msg.chat.id)
		handleAutoUnblock(chat = [msg.chat.id])
	if shouldDelete(msg):
		return deleteMsg(msg)
	if isNewUser(msg) and containRiskyWord(msg):
		markAction(msg, ban, True)
	remindIfNecessary(msg)
	if msg.from_user.id != BOT_OWNER:
		return
	if msg.text in ['spam', 'ban', 'b']:
		markAction(msg, ban)
	if msg.text == 'spam':
		context.bot.delete_message(
			chat_id=msg.chat_id, message_id=msg.reply_to_message.message_id)
	if msg.text in ['unban', 'w']:  
		markAction(msg, unban)

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
	deleteMsg(update.message)

dp = updater.dispatcher
dp.add_handler(
		MessageHandler(Filters.status_update.new_chat_members, handleJoin), group=1)
dp.add_handler(
		MessageHandler(Filters.status_update.left_chat_member, deleteMsgHandle), group = 2)
dp.add_handler(MessageHandler(Filters.group, handleGroup), group = 3)
dp.add_handler(MessageHandler(Filters.private, handlePrivate), group = 4)

updater.start_polling()
updater.idle()