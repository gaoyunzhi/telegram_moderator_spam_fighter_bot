from telegram_util import matchKey, getDisplayUser, cnWordCount, isInt
import yaml
import os
import plain_db

default_reason = '非常抱歉，机器人暂时无法判定您的消息，已转交人工审核。我们即将删除您这条发言，请注意保存。'

allowlist = plain_db.loadKeyOnlyDB('allowlist')
kicklist = plain_db.loadKeyOnlyDB('kicklist')
blocklist = plain_db.LargeDB('blocklist')

def highRiskUsr(user):
    name = user.first_name
    return isInt(name) and int(name) > 10000

def mediumRiskUsr(user):
    if user.username:
        return False
    if not user.last_name:
        return True
    if (user.last_name in user.first_name) or \
        (user.first_name in user.last_name):
        return True
    return False

def addBlacklist(text):
    text = text.strip()
    if not text or len(text) < 2:
        return 'no action'
    text = text.lower()
    blocklist.update(text, 6)

def badTextScore(text):
    if matchKey(text, allowlist.items()):
        return 0, []
    if not text:
        return 0, []
    result = {}
    for key, score in blocklist.items() + [(item, 10) for item in kicklist.items()]:
        if key.lower() in text.lower():
            result[key] = sore
    return sum(result.values()), result

def badText(text):
    score, result = badTextScore(text)
    if score < 10:
        return
    return ' '.join(result.keys())

def shouldKick(user):
    if len(user.first_name or '') + len(user.last_name or '') > 40:
        return True
    return badText(getDisplayUser(user))

def getTimeout(msg):
    if not msg.text:
        yield 5

    score, result = badTextScore(msg.text)
    if score >= 10:
        timeout = max(0, 7.5 / (0.2 ** score - 1) - 2.5) # 拍脑袋
        yield timeout
    if score > 0:
        yield 60

    if mediumRiskUsr(msg.from_user):
        yield 20
    if cnWordCount(msg.text) < 6:
        yield 60

    yield float('Inf')

def shouldDelete(msg):
    name = getDisplayUser(msg.from_user)
    if matchKey(name, allowlist):
        return float('Inf'), None

    if highRiskUsr(msg.from_user):
        return 0, None
    if msg.photo or msg.sticker or msg.video or msg.document:
        return 0, '非常抱歉，本群不支持多媒体信息。'
    if msg.forward_from or msg.forward_date:
        return 0, '非常抱歉，本群不支持转发信息。'
    if cnWordCount(msg.text) < 2:
        if len(msg.text) > 20:
            return 0, None
        return 20, None
    return sorted(list(getTimeout(msg)))[0], None