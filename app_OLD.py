from flask import Flask, request, jsonify
import requests

app = Flask(__name__)


####################### SHARED DATA #######################

works = []
workers = []

####################### GLOBAL VARS #######################

other_instance_ip = 'TODO'
max_workers = 5


####################### CLASSES #######################

class Work:
    def __init__(self, data, iterations, work_id, state):
        self.data = data
        self.iterations = iterations
        self.work_id = work_id
        self.state = state # out of: waiting / processing / done
        self.sha512 = None


class Worker:
    def __init__(self, worker_ip, state):
        self.worker_ip = worker_ip
        self.state = state # out of: idle / working / terminated


####################### FROM USER #######################



@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = int(request.args.get('iterations'))
    data = request.data
    work = Work(data, iterations, generate_work_id(), "waiting")
    works.append(work)
    share_work(work, other_instance_ip)

    worker = get_idle_worker()
    if not worker: worker = create_worker()
    if worker: launch_work(work, worker)

    return jsonify({'work_id': work.work_id}), 200
    


@app.route('/pullCompleted', methods=['POST'])
def pull_completed():
    top = int(request.args.get('top'))
    completed_works = [work for work in works if work.state == "done"]
    top_completed_works = completed_works[::-1][:top]
    completed_works_to_json = [{"work id":work.work_id, "sha512":work.sha512} for work in top_completed_works]
    return jsonify(completed_works_to_json), 200


####################### FROM OTHER INSTANCE #######################


@app.route('/updateWork', methods=['POST'])
def update_work():
    data = request.json.get('data')
    iterations = request.json.get('iterations')
    work_id = request.json.get('work_id')
    state = request.json.get('state')
    sha512 = request.json.get('sha512')

    corresponding_work = None

    for work in works:
        if work.work_id == work_id:
            corresponding_work = work
            break
            
    if corresponding_work:
        corresponding_work.state = state
        corresponding_work.sha512 = sha512
        return jsonify({'status': 'Work updated'}), 200

    # if the work is not found, add it
    else:
        work = Work(data, iterations, work_id, state)
        works.append(work)
        return jsonify({'status': 'Work added'}), 200




@app.route('/updateWorker', methods=['POST'])
def update_worker():
    worker_ip = request.json.get('worker_ip')
    state = request.json.get('state')

    corresponding_worker = None

    for worker in workers:
        if worker.worker_ip == worker_ip:
            corresponding_worker = worker
            break
    
    if corresponding_worker:
        if state == "terminated":
            workers.remove(corresponding_worker)
        else:
            corresponding_worker.state = state
        return jsonify({'status': 'Worker updated'}), 200

    # If the worker is not found, add it
    else:    
        worker = Worker(worker_ip, state)
        workers.append(worker)
        return jsonify({'status': 'Worker added'}), 200




####################### FROM WORKER #######################

# a route for the worker to send the result of the work
@app.route('/workDone', methods=['POST'])
def work_done():
    worker_ip = request.remote_addr
    work_id = int(request.json.get('work_id'))
    sha512 = request.json.get('sha512')
    
    for work in works:
        if work.work_id == work_id:
            work.state = "done"
            work.sha512 = sha512
            share_work(work, other_instance_ip)
            break

    for worker in workers:
        if worker.worker_ip == worker_ip:
            worker.state = "idle"
            share_worker(worker, other_instance_ip)
            ready_to_work(worker)
            break

    return jsonify({'status': 'Work done'}), 200



# a route for the worker to ask for self-termination
@app.route('/killMe', methods=['POST'])
def kill_me():
    worker_ip = request.remote_addr
    # TODO: terminate the ec2 machine of the sending worker
    
    for worker in workers:
        if worker.worker_ip == worker_ip:
            worker.state = "terminated"
            share_worker(worker, other_instance_ip)
            workers.remove(worker)
            break

    return jsonify({'status': 'Worker terminated'}), 200



####################### METHODS #######################


def generate_work_id():
    last_id = works[-1].work_id if works else -1
    return last_id + 1


def get_idle_worker():
    for worker in workers:
        if worker.state == "idle":
            return worker
    return None


def create_worker():
    if len(workers) >= max_workers:
        return None

    # TODO: create a new machine for the worker, using boto3
    ip = 'TODO'

    worker = Worker(ip, "idle")
    workers.append(worker)
    return worker


def ready_to_work(worker):
    for work in works:
        if work.state == "waiting":
            launch_work(work, worker)
            break


def launch_work(work, worker):
    # TODO: send the work to the machine of the worker
    work.state = "processing"
    worker.state = "working"
    share_work(work, other_instance_ip)
    share_worker(worker, other_instance_ip)
    

def share_worker(worker, ip):
    url = f'http://{ip}:5000/updateWorker'
    data = {'worker_ip': worker.worker_ip, 'state': worker.state}
    # requests.post(url, json=data)


def share_work(work, ip):
    url = f'http://{ip}:5000/updateWork'
    data = {'data': work.data, 'iterations': work.iterations, 'work_id': work.work_id, 'state': work.state, 'sha512': work.sha512}
    # requests.post(url, json=data)





####################### #######################

if __name__ == '__main__':
    app.run()
    requests.post()


