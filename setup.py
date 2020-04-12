import os
import sys

def kill():
	os.system("ps aux | grep ython | grep moderate | awk '{print $2}' | xargs kill -9")

def setup(mode):
	if mode == 'kill':
		kill()
		return

	RUN_COMMAND = 'nohup python3 -u moderate.py &'

	if mode != 'debug':
		r = os.system('pip3 install -r requirements.txt --upgrade')
		if r != 0:
			os.system('curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py')
			os.system('sudo python3 get-pip.py')
			os.system('rm get-pip.py')
			os.system('pip3 install -r requirements.txt --upgrade')
	kill()

	if mode.startswith('debug'):
		os.system(RUN_COMMAND[6:-2])
	else:
		os.system('touch nohup.out')
		os.system(RUN_COMMAND)
		os.system('tail -F nohup.out')


if __name__ == '__main__':
	if len(sys.argv) > 1:
		setup(sys.argv[1])
	else:
		setup('')