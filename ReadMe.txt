===================================================
- How to set everything up

1. Download these files to the same directory:
setup.sh
app.py
worker.py

2. Inside worker.py:
insert your access key and secret access key under CONSTANTS.

3. In aws configure:
switch to region 'us-east-1'

4. bash setup.sh
The IP's of the new machines will be printed.




After extensive work on this project, we didn't manage to address these issues, as mentioned in the code itself:

1. "workey.py" is not running correctly after creating an instance using Boto3 (spawn_worker method).

2. The main instances are unable to communicate with each other (pull_completed_internal method).








===================================================
- app_OLD.py

Our code is based on what was presented during the reception hour.
I have also attached the code for our first implementation.

General idea:

* Each instance holds a list of workers and a list of works,
and they should sync between them by sending the objects of the workers or works after each change.

* The main instances initiate the workers and the works when enqueue occurs,
and right after the initialization they actively send the work to the workers.

* The workers are waiting for work and never asking for it,
and if they are waiting for too long - they will ask for self termination.








===================================================
- Possible failure modes, and how to deal with them

1. Failure mode: If one or both EC2 instances go down, the system does not automatically detect the failure and re-run the instances.
Solution: Implement a monitoring mechanism that constantly checks the status of the EC2 instances. If an instance is detected as being down, the system should automatically initiate the process of launching replacement instances. This can be achieved by setting up health checks or utilizing AWS services like Auto Scaling Groups to ensure the desired number of instances is always running.

2. Failure mode: If the two EC2 instances lose connection between them, the system is unable to perform the pullCompleted method, resulting in the user not receiving the desired results.
Solution: Implement a centralized database that holds the information of the work_complete_queue for both EC2 instances. Each instance will send updates of their work_complete_queue to the database whenever it updates. This ensures that the user will always have access to the pullCompleted method.
The database acts as a reliable and synchronized source of information for the work_complete_queue. This approach provides fault tolerance and allows the user to retrieve the desired results regardless of the connectivity status between the EC2 instances.

3. Failure mode: Inconsistent workload may result in an abundance of creation and deletion of workers.
Solution: Implement a dynamic wait time for the deletion of workers that adjusts based on the workload provided. This approach ensures that workers are not excessively created or deleted, maintaining a more efficient and balanced system.

4. Failure mode: Load balancing problems may occur when one EC2 instance has a large work queue while the other EC2 instance has none. This will result in decreased productivity of the EC2 instances.
Solution: Implement a mechanism to balance the work queue between the two EC2 instances. When one EC2 instance has a significantly larger work queue compared to the other, it should distribute some of its workload to the other instance to achieve a more balanced distribution.
By implementing load balancing mechanisms, the system ensures that the workload is evenly distributed across the EC2 instances. This approach prevents bottlenecks, maximizes resource utilization, and maintains a balanced and efficient operation.