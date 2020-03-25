from telegram_util import matchKey, getDisplayUser
import yaml
import os

def highRiskUsr(user):
    try:
        if int(user.first_name) > 10000:
            return True
    except:
        pass
    return False

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
    lists = ['KICKLIST', 'MUTELIST', 'WHITELIST']

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
        lines = sorted([('%s: %f' % l).rstrip('0') for l in lines])
        with open('db/BLACKLIST', 'w') as f:
            f.write('\n'.join(lines))
        self.commit()
        
    def commit(self):
        os.system('git add . > /dev/null 2>&1 && git commit -m commit > /dev/null 2>&1 && git push -u -f > /dev/null 2>&1')

    def reduceBadness(self, text):
        text = text.strip()
        if not text:
            return
        text = text.lower()
        if text not in self.BLACKLIST:
            return
        self.BLACKLIST[text] -= 0.5
        if self.BLACKLIST[text] < 0.01:
            del self.BLACKLIST[text]
        self.saveBlacklist()

    def addBadness(self, text):
        text = text.strip()
        if not text:
            return
        text = text.lower()
        self.BLACKLIST[text] = self.BLACKLIST.get(text) + 0.5
        self.saveBlacklist()

    def badText(self, text):
        if matchKey(text, self.WHITELIST):
            return
        if not text:
            return
        result = {}
        for x in list(self.BLACKLIST.keys()) + list(self.KICKLIST):
            if x.lower() in text.lower():
                result[x] = self.BLACKLIST.get(x, 1)
        if sum(result.values()) < 1:
            return 
        return ' '.join(result.keys())

    def shouldKick(self, user):
        return self.badText(getDisplayUser(user))

    def highRiskText(self, text):
        if not text:
            return 'no text'
        if self.badText(text):
            return self.badText(text)
        for index, x in enumerate(text):
            if text[index:index + 3] == x * 3:
                return 'repeated ' + x

    def shouldLog(self, msg):
        if not self.replySender(msg) and not self.shouldDelete(msg):
            # good msg
            return False
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.MUTELIST):
            return False
        if msg.text and len(msg.text) < 6:
            return False
        if msg.forward_from:
            return 'forward'
        if msg.photo:
            return 'photo'
        if msg.sticker:
            return False
        if msg.video:
            return 'video'
        if msg.document:
            return 'document'
        if self.highRiskText(msg.text):
            detail = ''
            if len(msg.text) < 20:
                detail = ' msg: ' + msg.text
            return 'text contain: ' + self.highRiskText(msg.text) + detail
        return 'user name not set: ' + msg.text

    def replySender(self, msg):
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.WHITELIST):
            return
        if matchKey(name, self.MUTELIST):
            return
        if msg.text and len(msg.text) < 6:
            return '您的信息太短啦，为促进有效交流，我们即将删除您这条发言，请注意保存。欢迎修改后再发。'
        if mediumRiskUsr(msg.from_user):
            return '请先设置用户名再发言，麻烦您啦~ 我们即将删除您这条发言，请注意保存。'
        if msg.forward_from:
            return '您暂时不可以转发信息哦~ 已转交人工审核，审核通过会赋予您权限。'
        if msg.photo or msg.sticker or msg.video:
            return '您暂时不可以发多媒体信息哦~ 已转交人工审核，审核通过会赋予您权限。'
        if self.highRiskText(msg.text):
            return '您的消息被机器人认定为含有广告，已转交人工审核。'

    def shouldDelete(self, msg):
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.WHITELIST):
            return
        if matchKey(name, self.MUTELIST):
            return '请友善交流讨论。'
        if highRiskUsr(msg.from_user):
            return '请勿发表无关信息。'
        if not msg.text:
            return True
        if self.highRiskText(msg.text):
            return True
        if msg.forward_from or msg.photo or msg.sticker or msg.video:
            return True
        return

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
        self.commit()