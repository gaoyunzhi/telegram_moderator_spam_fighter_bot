from telegram_util import matchKey, getDisplayUser, cnWordCount, isInt
import yaml
import os
import plain_db

default_reason = '非常抱歉，机器人暂时无法判定您的消息，已转交人工审核。我们即将删除您这条发言，请注意保存。'

allowlist = plain_db.loadKeyOnlyDB('allowlist')
blocklist = plain_db.loadDB('blocklist')

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

class DB(object):
    lists = ['KICKLIST', 'WHITELIST']

    def readFile(self, filename):
        with open('db/' + filename) as f:
            content = [x.strip() for x in f.readlines()]
            setattr(self, filename, set([x for x in content if x]))

    def saveFile(self, filename):
        with open('db/' + filename, 'w') as f:
            f.write('\n'.join(sorted(getattr(self, filename))))

    def __init__(self):
        for l in self.lists:
            self.readFile(l)
        with open('db/BLACKLIST') as f:
            lines = [x.strip().split(':') for x in f.readlines() if x.strip()]
        self.BLACKLIST = {line[0].strip().lower(): float(line[1]) 
            for line in lines if line[0] and line[0].strip()}

    def saveBlacklist(self):
        lines = [(k.strip().lower(), v) for (k, v) in self.BLACKLIST.items() 
            if k and k.strip()]
        lines = sorted([('%s: %f' % l).rstrip('0').rstrip('.') for l in lines])
        with open('db/BLACKLIST', 'w') as f:
            f.write('\n'.join(lines))
        commit()

    def setBadness(self, text, weight):
        text = text.strip()
        if not text:
            return 'no action'
        text = text.lower()
        self.BLACKLIST[text] = weight
        if weight == 0:
            del self.BLACKLIST[text]
        self.saveBlacklist()
        return text + ' badness: ' + str(self.BLACKLIST.get(text, 0))

    def badTextScore(self, text):
        if matchKey(text, self.WHITELIST):
            return 0, []
        if not text:
            return 0, []
        result = {}
        for x in list(self.BLACKLIST.keys()) + list(self.KICKLIST):
            if x.lower() in text.lower():
                result[x] = self.BLACKLIST.get(x, 1)
        return sum(result.values()), result

    def badText(self, text):
        score, result = self.badTextScore(text)
        if score < 1:
            return
        return ' '.join(result.keys())

    def shouldKick(self, user):
        if len(user.first_name or '') + len(user.last_name or '') > 80:
            return True
        return self.badText(getDisplayUser(user))

    def shouldLog(self, msg):
        if self.shouldDelete(msg)[0] == float('Inf'):
            # good msg
            return False
        name = getDisplayUser(msg.from_user)
        if msg.forward_from or msg.forward_date or not msg.text:
            return False
        if cnWordCount(msg.text) < 10 or self.badTextScore(msg.text)[0] > 2:
            return False
        if self.badText(msg.text):
            detail = ''
            if len(msg.text) < 40:
                detail = ' msg: ' + msg.text
            return 'text contain: ' + self.badText(msg.text) + detail
        return False # user name not set

    def shouldDeleteReasons(self, msg):
        if not msg.text:
            yield (5, None) # shouldn't be here

        score, result = self.badTextScore(msg.text)
        if score >= 1: # may need revisit
            timeout = max(0, 7.5 / (2 ** score - 1) - 2.5) # 拍脑袋
            yield (timeout, default_reason)
        if score > 0:
            yield (60, None)

        if mediumRiskUsr(msg.from_user):
            yield (20, '请先设置用户名再发言，麻烦您啦~ 我们将在20分钟后删除您这条发言，请注意保存。')
        if cnWordCount(msg.text) < 6:
            yield (60, None)

        yield (float('Inf'), None)

    def shouldDelete(self, msg):
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.WHITELIST):
            return float('Inf'), None

        # delete immediately
        if highRiskUsr(msg.from_user):
            return 0, default_reason
        if msg.photo or msg.sticker or msg.video or msg.document:
            return 0, '您暂时不可以发多媒体信息哦~ 已转交人工审核，审核通过会赋予您权限。'
        if msg.forward_from or msg.forward_date:
            return 0, '您暂时不可以转发信息哦~ 已转交人工审核，审核通过会赋予您权限。'
        if cnWordCount(msg.text) < 2:
            return 0, default_reason

        return sorted(list(self.shouldDeleteReasons(msg)))[0]

    def getPermission(self, target):
        tid = str(target.id)
        for l in self.lists:
            if tid in getattr(self, l):
                return l[0].lower()

    def record(self, mlist, target):
        tid = str(target.id)
        for l in self.lists:
            if l == mlist:
                getattr(self, l).add(tid)
            else:
                getattr(self, l).discard(tid)
            self.saveFile(l)
        commit()