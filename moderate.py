#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
import time
import os
import traceback as tb
from telegram_util import getDisplayUser, log_on_fail, getTmpFile, autoDestroy, matchKey
import yaml


JOIN_TIME = {}
NEW_USER_WAIT_TIME = 3600 * 8

with open('CREDENTIALS') as f:
    CREDENTIALS = yaml.load(f, Loader=yaml.FullLoader)

updater = Updater(CREDENTIALS['token'], use_context=True)
r = updater.bot.send_message(chat_id=-1001198682178, text='test')
r.delete()
debug_group = r.chat
this_bot = r.from_user.id
BOT_OWNER = CREDENTIALS['owner']

quotes = ["'", '"', '‘', '“', '【']

with open('BETTER_AVOID_WORDS') as f:
    better_avoid_words = set(yaml.load(f, Loader=yaml.FullLoader))

with open('BLACKLIST') as f:
	BLACKLIST = [x.strip() for x in f.readlines()]
	BLACKLIST = set([x for x in BLACKLIST if x])

with open('KICK_KEYS') as f:
    KICK_KEYS = set(yaml.load(f, Loader=yaml.FullLoader))

def saveBlacklist():
	with open('BLACKLIST', 'w') as f:
		f.write('\n'.join(sorted(BLACKLIST)))

def needKick(user):
	name = getDisplayUser(user)
	return matchKey(name, KICK_KEYS)

def ban(bad_user):
	if bad_user.id == this_bot:
		return  # don't ban the bot itself :p
	if str(bad_user.id) in BLACKLIST:
		debug_group.send_message(
			text=getDisplayUser(bad_user) + ' already banned',
			parse_mode='Markdown')
		return
	BLACKLIST.add(str(bad_user.id))
	saveBlacklist()
	debug_group.send_message(
		text=getDisplayUser(bad_user) + ' banned',
		parse_mode='Markdown')

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	for member in msg.new_chat_members:
		if needKick(member):
			context.bot.kick_chat_member(msg.chat.id, member.id)
			ban(member)
			debug_group.send_message(
				getDisplayUser(member) + ' kicked from ' + getGroupName(msg),
				parse_mode='Markdown',
				disable_web_page_preview=True)
			continue
		if member.id != this_bot and member.id not in JOIN_TIME:
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

def containRiskyWord(msg):
	if not msg.text:
		return False
	for b in BLACKLIST:
		if b.lower() in msg.text.lower():
			return True
	return False

def isBlockedUser(id):
	return str(id) in BLACKLIST

def shouldDelete(msg):
	return (isNewUser(msg) and (isMultiMedia(msg) or containRiskyWord(msg))) \
	 or isBlockedUser(msg.from_user.id)

def getGroupName(msg):
	return '[' + (msg.chat.title or str(msg.chat.id)) + \
		'](t.me/' + (msg.chat.username or '') + ')'

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
	text = msg.text
	if text:
		text = ': ' + text
	else:
		text = ''
	action_users = getActionUsers(msg)
	names = ', '.join([getDisplayUser(x) for x in action_users])
	debug_group.send_message(
		text=names + ' ' + getMsgType(msg) + 
		' ' + getGroupName(msg) + text,
		parse_mode='Markdown',
		disable_web_page_preview=True)
	if msg.photo:
		filename = getTmpFile(msg)
		debug_group.send_photo(photo=open(filename, 'rb'))
		os.system('rm ' + filename)
	if msg.video:
		filename = getTmpFile(msg)
		debug_group.send_document(document=open(filename, 'rb'))
		os.system('rm ' + filename)
	msg.delete()

def unban(not_so_bad_user):
	if str(not_so_bad_user.id) not in BLACKLIST:
		debug_group.send_message(
			text=getDisplayUser(not_so_bad_user) + ' not banned',
			parse_mode='Markdown')
		return
	BLACKLIST.remove(str(not_so_bad_user.id))
	saveBlacklist()
	debug_group.send_message(
		text=getDisplayUser(not_so_bad_user) + ' unbanned',
		parse_mode='Markdown')

def markAction(msg, action):
	if not msg.reply_to_message:
		return
	for item in msg.reply_to_message.entities:
		if item['type'] == 'text_mention':
			action(item.user)
			return
	action(msg.reply_to_message.from_user)
	if msg.chat_id != debug_group.id:
		r = msg.reply_text('请大家互相理解，友好交流。')
		r.delete()
		msg.delete()

@log_on_fail(debug_group)
def remindIfNecessary(msg):
	if not msg.text:
		return
	if matchKey(msg.text, better_avoid_words) and not matchKey(msg.text, quotes):
		reminder = '建议避免使用带有强烈主观判断的词哦，比如：' + ', '.join(better_avoid_words) + \
			'。 谢谢啦！'
		autoDestroy(msg.reply_text(reminder), 10)
	emotional_words = ['意淫', '凭什么']
	if matchKey(msg.text, emotional_words) or msg.text.count('?') + msg.text.count('？') >= 3:
		reminder = '反问，反讽不利于友好交流哦，建议您换成大家更容易理解的表达哦。谢谢啦！'
		autoDestroy(msg.reply_text(reminder), 10)
	attacking_words = ['太low']
	if matchKey(msg.text, attacking_words):
		reminder = '请友好交流，争取互相理解。谢谢啦！'
		autoDestroy(msg.reply_text(reminder), 10)

@log_on_fail(debug_group)
def handleGroup(update, context):
	msg = update.message
	if not msg:
		return
	if shouldDelete(msg):
		return deleteMsg(msg)
	remindIfNecessary(msg)
	if msg.from_user.id != BOT_OWNER:
		return
	if msg.text in ['spam', 'ban']:
		markAction(msg, ban)
	if msg.text == 'spam':
		context.bot.delete_message(
			chat_id=msg.chat_id, message_id=msg.reply_to_message.message_id)
	if msg.text == 'unban':  
		markAction(msg, unban)

def handlePrivate(update, context):
	update.message.reply_text(
		'Add me to the group promote me as admin please.')

def deleteMsgHandle(update, context):
	deleteMsg(update.message)

dp = updater.dispatcher
dp.add_handler(
		MessageHandler(Filters.status_update.new_chat_members, handleJoin), group=2)
dp.add_handler(
		MessageHandler(Filters.status_update.new_chat_members, deleteMsgHandle), group = 1)
dp.add_handler(
		MessageHandler(Filters.status_update.left_chat_member, deleteMsgHandle), group = 1)
dp.add_handler(MessageHandler(Filters.group, handleGroup), group = 3)
dp.add_handler(MessageHandler(Filters.private, handlePrivate), group = 4)

updater.start_polling()
updater.idle()