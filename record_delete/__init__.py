from telegram_util import getDisplayUser

def getGroupName(chat, tele):
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
	if msg.document:
		return 'send document in'
	return 'did some action'

def recordDelete(msg, debug_group, tele, p):
	try:
		msg.delete()
	except:
		return
	if p:
		p = ' (' + p + ')'
	r = debug_group.send_message(
		text='%s %s %s' % (getDisplayUser(msg.from_user) + p, 
			getMsgType(msg), getGroupName(msg.chat, tele))
		parse_mode='Markdown',
		disable_web_page_preview=True)
	if not r.entities or len(r.entities) != 2:
		r.delete() # not actionable
