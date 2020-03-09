from telegram_util import matchKey, getDisplayUser

def highRiskUsr(user):
    name = getDisplayUser(user).lower()
    try:
        int(user.first_name)
        return True
    except:
        pass
    return not user.last_name and not user.username

class DB(object):
    def readFile(self, filename):
        with open('db/' + filename) as f:
            content = [x.strip() for x in f.readlines()]
            setattr(self, filename, set([x for x in content if x]))

    def __init__(self):
        self.readFile('KICKLIST')
        self.readFile('MUTELIST')
        self.readFile('NAME_BLACKLIST')
        self.readFile('WHITELIST')

    def badText(self, text):
        if matchKey(text, self.WHITELIST):
            return False
        return matchKey(text, self.NAME_BLACKLIST) or \
            matchKey(text, self.KICKLIST)

    def shouldKick(self, user):
        return self.badText(getDisplayUser(user))

    def highRiskText(self, text):
        if self.badText(text):
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

    def saveList():
        with open('BLACKLIST', 'w') as f:
            f.write('\n'.join(sorted(BLACKLIST)))
        with open('WHITELIST', 'w') as f:
            f.write('\n'.join(sorted(WHITELIST)))