import traceback as tb
import yaml
import time

def readFile(filename):
    with open('db/' + filename) as f:
        content = [x.strip() for x in f.readlines()]
        return set([x for x in content if x])

class QUEUE(object):
    def __init__(self):
        try:
            with open('queue.yaml') as f:
                self.queue = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            print(e)
            tb.print_exc()
            self.queue = []

            with open('BLACKLIST') as f:
    BLACKLIST = [x.strip() for x in f.readlines()]
    BLACKLIST = set([x for x in BLACKLIST if x])

    try:
        with open('WHITELIST') as f:
            WHITELIST = [x.strip() for x in f.readlines()]
            WHITELIST = set([x for x in WHITELIST if x])
    except:
        WHITELIST = set()

    with open('KICK_KEYS') as f:
        KICK_KEYS = set(yaml.load(f, Loader=yaml.FullLoader))

    def saveList():
        with open('BLACKLIST', 'w') as f:
            f.write('\n'.join(sorted(BLACKLIST)))
        with open('WHITELIST', 'w') as f:
            f.write('\n'.join(sorted(WHITELIST)))

    def append(self, x):
        self.queue.append(x)
        self.save()

    def pop(self):
        x = self.queue.pop()
        self.save()
        return x

    def empty(self):
        return len(self.queue) == 0

    def save(self):
        with open('queue.yaml', 'w') as f:
            f.write(yaml.dump(self.queue, sort_keys=True, indent=2))

class UPDATE_TIME(object):
    def __init__(self):
        try:
            with open('update_time.yaml') as f:
                self.UPDATE_TIME = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            print(e)
            tb.print_exc()
            self.UPDATE_TIME = {}

    def setTime(self, chat_id):
        self.UPDATE_TIME[chat_id] = time.time()
        self.save()

    def setPause(self, chat_id):
        self.UPDATE_TIME[chat_id] = time.time() + 4 * 60 * 60
        self.save()

    def get(self, chat_id):
        return self.UPDATE_TIME.get(chat_id, 0)

    def save(self):
        with open('update_time.yaml', 'w') as f:
            f.write(yaml.dump(self.UPDATE_TIME, sort_keys=True, indent=2))

class SUBSCRIPTION(object):
    def __init__(self):
        try:
            with open('subscription.yaml') as f:
                self.SUBSCRIPTION = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            print(e)
            tb.print_exc()
            self.SUBSCRIPTION = {}

    def getList(self, chat_id):
        return self.SUBSCRIPTION.get(chat_id, [])

    def deleteIndex(self, chat_id, index):
        try:
            del self.SUBSCRIPTION[chat_id][index]
            self.save()
            return 'success'
        except Exception as e:
            return str(e)

    def getSubsribers(self, chat_id):
        result = []
        for subscriber, items in self.SUBSCRIPTION.items():
            for item in items:
                if item['id'] == chat_id:
                    result.append(subscriber)
                    break
        return result

    def add(self, chat_id, chat):
        self.SUBSCRIPTION[chat_id] = self.SUBSCRIPTION.get(chat_id, [])
        if chat['id'] in [x['id'] for x in self.SUBSCRIPTION[chat_id]]:
            return 'FAIL: subscripion already exist.'
        self.SUBSCRIPTION[chat_id].append(chat)
        self.save()
        return 'success'

    def save(self):
        with open('subscription.yaml', 'w') as f:
            f.write(yaml.dump(self.SUBSCRIPTION, sort_keys=True, indent=2))