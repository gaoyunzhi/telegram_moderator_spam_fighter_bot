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

def recordDelete(msg, debug_group, tele, p, reason):
	if p:
		p = ' (' + p + ')'
	else:
		p = ''
	r = debug_group.send_message(
		text='%s | %s | %s' % (getGroupName(msg.chat, tele),
			getDisplayUser(msg.from_user) + p, reason),
		parse_mode='Markdown',
		disable_web_page_preview=True)
	for item in r.entities:
		if item['type'] == 'text_mention' and item.user:
			return
	r.delete()
