#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram import ChatPermissions
import time
import os
import traceback as tb
from telegram_util import getDisplayUser, log_on_fail, getTmpFile, autoDestroy, matchKey
import yaml
from db import DB

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

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	kicked = False
	for member in msg.new_chat_members:
		if db.needKick(member):
			tele.kick_chat_member(msg.chat.id, member.id)
			kicked = True
	if not kicked:
		autoDestroy(msg.reply_text('欢迎新朋友！新朋友请自我介绍~'))

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
	try:
		msg.delete()
	except:
		return
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

def unban(not_so_bad_user):
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

def mute(bad_user):
	if bad_user.id in [this_bot, BOT_OWNER]:
		return  # don't ban the bot itself :p
	if str(bad_user.id) in db.MUTELIST:
		debug_group.send_message(
			text=getDisplayUser(bad_user) + ' already banned',
			parse_mode='Markdown')
		return
	BLACKLIST.add(str(bad_user.id))
	saveList()
	debug_group.send_message(
		text=getDisplayUser(bad_user) + ' banned',
		parse_mode='Markdown')

def doAction(usr, action):
	r = action(usr)
	if r:
		db.save()
		debug_group.send_message(
			text=getDisplayUser(usr) + ': ' + action.__name__,
			parse_mode='Markdown')
	else:
		debug_group.send_message(
			text=getDisplayUser(usr) + ': stay ' + action.__name__,
			parse_mode='Markdown')

def markAction(msg, action)
	if not msg.reply_to_message:
		return
	for item in msg.reply_to_message.entities:
		if item['type'] == 'text_mention':
			doAction(item.user, action)
			return
	if msg.chat_id != debug_group.id:
		doAction(msg.reply_to_message.from_user, action)
		r = msg.reply_text('-')
		r.delete()
		msg.delete()
		return 
	doAction(msg.reply_to_message.forward_from, action)

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

@log_on_fail(debug_group)
def handleGroup(update, context):
	msg = update.effective_message
	if not msg:
		return

	if msg.chat_id != debug_group.id:
		global chats
		if not msg.chat.id in chats:
			chats.add(msg.chat.id)
			handleAutoUnblock(chat = [msg.chat.id])
		if db.needKick(msg.from_user):
			tele.kick_chat_member(msg.chat.id, member.id)
		if db.shouldDelete(msg):
			return deleteMsg(msg)

	if msg.from_user.id != BOT_OWNER:
		return
	# TODO: check do I need to mute anyone? Why not just kick them?
	if msg.text in ['spam', 'ban', 'b', 'x']:
		markAction(msg, mute)
	if msg.text in ['kick', 'k']:
		markAction(msg, kick)
	if msg.text in ['w']:  
		markAction(msg, white)
	if msg.text in ['uw', 'unwhitelist']:  
		markAction(msg, unwhite)

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
dp.add_handler(
		MessageHandler(Filters.status_update.new_chat_members, handleJoin), group=1)
dp.add_handler(
		MessageHandler(Filters.status_update.left_chat_member or Filters.status_update.new_chat_members, deleteMsgHandle), group = 2)
dp.add_handler(MessageHandler(Filters.group, handleGroup), group = 3)
dp.add_handler(MessageHandler(Filters.private, handlePrivate), group = 4)

updater.start_polling()
updater.idle()