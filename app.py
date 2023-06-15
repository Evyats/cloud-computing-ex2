from flask import Flask, request, jsonify
from datetime import datetime
import requests
import threading
import json
import os
import boto3


################# CONSTANTS #################

ACCESS_KEY = ''
SECRET_ACCESS_KEY = ''

MAX_NUM_OF_WORKERS = 3
TIMER = 10                  # seconds
WORK_MAX_WAIT_TIME = 15     # seconds

################# GLOBAL VARS #################

app = Flask(__name__)

this_node_ip = 'not yet updated'
other_node_ip = 'other node not yet created / known'
last_work_id = 0

work_queue = []             # dictionaries of: {work_id, data, iterations, arrived_at}
work_complete_queue = []    # dictionaries of: {work_id, sha512}

workers = []                # ONLY for worker termination purposes

num_of_workers = 0




################# METHODS #################

def spawn_workers_handler():
    global num_of_workers
    if work_queue:
        first_work_arrival = work_queue[0]['arrived_at']
        work_waiting_time = (datetime.now() - first_work_arrival).seconds
        if work_waiting_time > WORK_MAX_WAIT_TIME:
            if num_of_workers < MAX_NUM_OF_WORKERS:
                num_of_workers += 1
                spawn_worker()
    threading.Timer(TIMER, spawn_workers_handler).start()


def generate_work_id():
    global last_work_id
    last_work_id += 2
    return last_work_id - 2



def spawn_worker(): 
    return
    # TODO: fix the code below so the worker.py will run correctly on the new instance

    aws_access_key_id = ACCESS_KEY
    aws_secret_access_key = SECRET_ACCESS_KEY
    region = 'us-east-1'
    
    current_directory = os.path.dirname(os.path.abspath(__file__))
    script_file = os.path.join(current_directory, 'worker.py')
    with open(script_file, 'r') as file:
        script_content = file.read()

    userData = f"""#!/bin/bash
    exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
    apt-get -y update
    apt-get -y install python3
    apt-get -y install python3-pip
    pip install flask requests
    umask 000
    echo "{script_content}" >> /home/ubuntu/worker.py
    nohup python3 /home/ubuntu/worker.py {this_node_ip} {other_node_ip} >> /home/ubuntu/output.txt 2>&1 &
    """

    ec2_resource = boto3.resource('ec2', region_name=region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    
    instance_params = {
        'ImageId': 'ami-042e8287309f5df03',
        'InstanceType': 't3.micro',
        'KeyName': 'cloud-course',
        'MinCount': 1,
        'MaxCount': 1,
        'UserData': userData
    }
    
    instances = ec2_resource.create_instances(**instance_params)

    # Wait for the instance to be running
    for instance in instances:
        instance.wait_until_running()
        instance.reload()
        workers.append(instance)
        print('New instance created!')
        print('Instance ID:', instance.id)
        print('Public IP:', instance.public_ip_address)



def terminate_worker(worker_ip):
    for worker in workers:
        if worker.public_ip_address == worker_ip:
            worker.terminate()
            break





################# USER ENDPOINTS #################

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    work_dict = {
        'work_id': generate_work_id(),
        'data': request.data.decode('utf-8'),
        'iterations': int(request.args.get('iterations')),
        'arrived_at': datetime.now()
    }
    work_queue.append(work_dict)
    return jsonify(work_dict['work_id'])


@app.route('/pullCompleted', methods=['POST'])
def pull_completed():
    global work_complete_queue
    top = int(request.args.get('top'))
    top_work_complete = work_complete_queue[:top]
    work_complete_queue = work_complete_queue[top:]

    if len(top_work_complete) != 0:
        return jsonify(top_work_complete)

    try:
        req = requests.post(f'http://{other_node_ip}:5000/pullCompletedInternal?top={str(top)}')
        return json.loads(req.text)
    except:
        return jsonify([])


@app.route('/pullCompletedInternal', methods=['POST'])
def pull_completed_internal():
    return jsonify([])
    # TODO: fix the code below so the main instances will be able to communicate with each other
    global work_complete_queue
    top = int(request.args.get('top'))
    top_work_complete = work_complete_queue[:top]
    work_complete_queue = work_complete_queue[top:]
    result = jsonify(top_work_complete)
    return result




################# WORKER ENDPOINTS #################


@app.route('/giveMeWork', methods=['POST'])
def give_me_work():
    if work_queue:
        return jsonify(work_queue.pop(0))
    return jsonify(None)


@app.route('/workComplete', methods=['POST'])
def work_complete():
    completed_dict = {
        'work_id': int(request.args.get('work_id')),
        'sha512': request.args.get('sha512')
    }
    work_complete_queue.append(completed_dict)
    return '', 200
    

@app.route('/killMe', methods=['POST'])
def kill_me():
    global num_of_workers
    worker_ip = request.remote_addr
    terminate_worker(worker_ip)
    num_of_workers -= 1
    return '', 200


################# SCRIPT ENDPOINTS #################

@app.route('/startTimer', methods=['POST'])
def start_timer():
    print("Starting timer")
    spawn_workers_handler()
    return '', 200

@app.route('/updateIps', methods=['POST'])
def add_sibling():
    global this_node_ip
    global other_node_ip
    this_node_ip = request.args.get('thisNodeIp')
    other_node_ip = request.args.get('otherNodeIp')
    return '', 200

@app.route('/setSecondNode', methods=['POST'])
def set_second_node():
    global last_work_id
    last_work_id = 1
    return '', 200



################# DEBUGGING ENDPOINTS #################

@app.route('/debug', methods=['POST'])
def debug():
    current_state = {
        'work_queue': work_queue,
        'work_complete_queue': work_complete_queue,
        'num_of_workers': num_of_workers,
        'other_node_ip': other_node_ip,
        'this_node_ip': this_node_ip
    }
    return jsonify(current_state)



################# INITIALIZATION #################

if __name__ == '__main__':
    # spawn_workers_handler()
    app.run()
