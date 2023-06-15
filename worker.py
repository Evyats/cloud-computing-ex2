import sys
import time
from datetime import datetime
import requests
import json
import hashlib

################# CONSTANTS #################

MAX_TIME_WAIT = 20 # seconds
TIME_BETWEEN_ITERATIONS = 10 # seconds


################# GLOBAL VARS #################

creator_ip = sys.argv[1]
siblings_ip = sys.argv[2]
# creator_ip = '35.174.171.49'
# siblings_ip = '3.95.191.28'

################# METHODS #################


def work_loop():
    nodes = [creator_ip, siblings_ip]
    last_time = datetime.now()

    while (datetime.now() - last_time).seconds <= MAX_TIME_WAIT:
        work_was_done = False
        for node in nodes:
            work = ask_for_work(node)
            if work:
                work_dict = json.loads(work)
                if work_dict != None:
                    work_was_done = True
                    result = do_work(work_dict['data'], int(work_dict['iterations']))
                    send_completed_work(node, work_dict['work_id'], result)
                    last_time = datetime.now()
        if not work_was_done:
            time.sleep(TIME_BETWEEN_ITERATIONS)
    
    ask_for_self_termination(creator_ip)


def ask_for_work(node):
    try:
        return requests.post(f'http://{node}:5000/giveMeWork').text
    except:
        return None


def do_work(data, iterations):
    buffer = data.encode('utf-8')
    output = hashlib.sha512(buffer).digest()
    for _ in range(iterations - 1):
        output = hashlib.sha512(output).digest()
    return output.hex()


def send_completed_work(node, work_id, sha512):
    try:
        requests.post(f'http://{node}:5000/workComplete?work_id={work_id}&sha512={sha512}')
    except:
        pass


def ask_for_self_termination(node):
    try:
        requests.post(f'http://{node}:5000/killMe')
    except:
        pass




################# INITIALIZATION #################

if __name__ == '__main__':
    work_loop()