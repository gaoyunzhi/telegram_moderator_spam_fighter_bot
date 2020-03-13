from telegram_util import matchKey, getDisplayUser

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
        self.readFile('NAME_BLACKLIST')

    def badText(self, text):
        if matchKey(text, self.WHITELIST):
            return False
        return matchKey(text, self.NAME_BLACKLIST) or \
            matchKey(text, self.KICKLIST)

    def shouldKick(self, user):
        return self.badText(getDisplayUser(user))

    def highRiskText(self, text):
        if not text or self.badText(text):
            return True
        for index, x in enumerate(text):
            if text[index:index + 3] == x * 3:
                return True

    def shouldLog(self, msg):
        if not replySender(msg) and not shouldDelete(msg):
            # good msg
            return False
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.MUTELIST):
            return False
        if msg.text and len(msg.text) < 3:
            return False
        return True

    def replySender(msg):
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
        if self.highRiskText(name):
            return '您的用户名被机器人认定为含有广告，已转交人工审核。'

    def shouldDelete(self, msg):
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.WHITELIST):
            return False
        if highRiskUsr(msg.from_user):
            return True
        if not msg.text:
            return True
        if self.highRiskText(msg.text) or self.highRiskText(name):
            return True
        if msg.forward_from or msg.photo or msg.sticker or msg.video:
            return True
        return False

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