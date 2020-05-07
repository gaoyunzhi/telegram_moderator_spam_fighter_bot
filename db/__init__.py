from telegram_util import matchKey, getDisplayUser
import yaml
import os
import threading

def commit():
    # see if I need to deal with race condition
    command = 'git add . > /dev/null 2>&1 && git commit -m commit > /dev/null 2>&1 && git push -u -f > /dev/null 2>&1'
    threading.Timer(60, lambda: os.system(command)).start()

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

class GroupSetting(object):
    def __init__(self):
        with open('db/SETTING') as f:
            content = yaml.load(f, Loader=yaml.FullLoader)
        self.greeting = content.get('greeting', {})
        self.disable_moderation = content.get('disable_moderation', [])

    def getGreeting(self, chat_id):
        return self.greeting.get(chat_id, '欢迎新朋友！新朋友请自我介绍~')

    def setGreeting(self, chat_id, text):
        self.greeting[chat_id] = text
        self.save()

    def setDisableModeration(self, chat_id, b):
        if not b and chat_id in self.disable_moderation:
            self.disable_moderation.remove(chat_id)
        if b and not chat_id in self.disable_moderation:
            self.disable_moderation.append(chat_id)
            self.disable_moderation.sort()
        self.save()

    def isModerationDisabled(self, chat_id):
        return chat_id in self.disable_moderation

    def save(self):
        with open('db/SETTING', 'w') as f:
            f.write(yaml.dump({
                'greeting': self.greeting, 
                'disable_moderation': self.disable_moderation,
            }, sort_keys=True, indent=2))
        commit()

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
        lines = sorted([('%s: %f' % l).rstrip('0').rstrip('.') for l in lines])
        with open('db/BLACKLIST', 'w') as f:
            f.write('\n'.join(lines))
        commit()

    def reduceBadness(self, text):
        text = text.strip()
        if not text:
            return 'no action'
        text = text.lower()
        if text not in self.BLACKLIST:
            return 'no action'
        self.BLACKLIST[text] -= 0.5
        if self.BLACKLIST[text] < 0.01:
            del self.BLACKLIST[text]
        self.saveBlacklist()
        return text + ' badness: ' + str(self.BLACKLIST.get(text, 0))

    def addBadness(self, text):
        text = text.strip()
        if not text:
            return 'no action'
        text = text.lower()
        self.BLACKLIST[text] = self.BLACKLIST.get(text, 0.0) + 0.5
        self.saveBlacklist()
        return text + ' badness: ' + str(self.BLACKLIST[text])

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

    def highRiskText(self, text):
        if not text:
            return 'no text'
        if self.badText(text):
            return self.badText(text)

    def shouldLog(self, msg):
        if not self.replySender(msg) and not self.shouldDelete(msg):
            # good msg
            return False
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.MUTELIST):
            return False
        if msg.text and len(msg.text) < 6:
            return False
        if msg.forward_from or msg.forward_date:
            return False
        if msg.photo:
            return 'photo'
        if msg.sticker:
            return False
        if msg.video:
            return 'video'
        if msg.document:
            return 'document'
        if not msg.text:
            return 'no text'
        if self.badTextScore(msg.text)[0] > 2:
            return False
        if self.highRiskText(msg.text):
            detail = ''
            if len(msg.text) < 20:
                detail = ' msg: ' + msg.text
            return 'text contain: ' + self.highRiskText(msg.text) + detail
        return False # user name not set

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
        if msg.photo or msg.sticker or msg.video:
            return '您暂时不可以发多媒体信息哦~ 已转交人工审核，审核通过会赋予您权限。'
        if msg.forward_from or msg.forward_date:
            return '您暂时不可以转发信息哦~ 已转交人工审核，审核通过会赋予您权限。'
        if self.highRiskText(msg.text):
            return '非常抱歉，机器人暂时无法判定您的消息，已转交人工审核。'

    def shouldDelete(self, msg):
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.WHITELIST):
            return
        if matchKey(name, self.MUTELIST):
            return '非常抱歉，机器人暂时无法判定您的消息，已转交人工审核。'
        if highRiskUsr(msg.from_user):
            return '非常抱歉，机器人暂时无法判定您的消息，已转交人工审核。'
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
        commit()