from telegram_util import matchKey, getDisplayUser, cnWordCount, isInt
import plain_db

allowlist = plain_db.loadKeyOnlyDB('allowlist')
kicklist = plain_db.loadKeyOnlyDB('kicklist')
blocklist = plain_db.LargeDB('blocklist', isIntValue=True)

def addBlocklist(text):
    text = text.strip()
    if not text or len(text) < 2:
        return 'no action'
    text = text.lower()
    blocklist.update(text, 6)
    return 'success'

def badTextScore(text):
    if not text:
        return 0, []
    result = {}
    for key, score in blocklist.items() + [
            (item, 10) for item in kicklist.items()]:
        if key.lower() in text.lower():
            result[key] = score
    return sum(result.values()), result

def badText(text):
    score, result = badTextScore(text)
    if score < 10:
        return
    return ' '.join(result.keys())

def shouldKick(user):
    name = user.first_name
    if isInt(name) and int(name) > 10000:
        return True
    if len(name) + len(user.last_name or '') > 40:
        return True
    return badText(getDisplayUser(user))

def getTimeout(msg):
    score, result = badTextScore(msg.text)
    if score >= 10:
        timeout = max(0, 7.5 / (0.2 * score - 1) - 2.5) # 拍脑袋
        yield timeout
    if score > 0:
        yield 60
    if cnWordCount(msg.text) < 6:
        yield 60

    yield float('Inf')

def shouldDelete(msg):
    if str(msg.from_user.id) in allowlist.items():
        return float('Inf'), None
    if not msg.text:
        return 0, '非常抱歉，本群不支持多媒体信息。'
    if msg.forward_from or msg.forward_date:
        return 0, '非常抱歉，本群不支持转发信息。'
    if cnWordCount(msg.text) < 2:
        if len(msg.text) > 10:
            return 0, None
        return 20, None
    return sorted(list(getTimeout(msg)))[0], None