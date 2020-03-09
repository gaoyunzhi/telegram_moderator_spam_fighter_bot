from telegram_util import matchKey, getDisplayUser

def highRiskUsr(user):
    name = getDisplayUser(user).lower()
    try:
        int(user.first_name)
        return True
    except:
        pass
    if user.username:
        if (user.last_name in user.first_name) or \
            (user.first_name in user.last_name):
            return True
    elif not user.username:
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
        if not test or self.badText(text):
            return True
        for index, x in enumerate(text):
            if text[index:index + 3] == x * 3:
                return True

    def shouldDelete(self, msg):
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.WHITELIST):
            return False
        if matchKey(name, self.MUTELIST) or highRiskUsr(msg.from_user):
            return True
        if self.highRiskText(msg.text) or self.highRiskText(name):
            return True
        if msg.forward_from or msg.photo or msg.sticker or msg.video:
            return True
        if msg.text:
            return False
        return True

    def record(self, mlist, target):
        for l in self.lists:
            if l == mlist:
                getattr(self, l).add(target.id)
                continue
            getattr(self, l).discard(target.id)
            self.saveFile(l)