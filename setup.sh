# debug
# set -o xtrace

KEY_NAME="cloud-course"
KEY_PEM="$KEY_NAME.pem"
PYTHON_FILE_NAME="app.py"

echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME \
    | jq -r ".KeyMaterial" > $KEY_PEM

# secure the key pair
chmod 400 $KEY_PEM

SEC_GRP="my-sg-`date +'%N'`"

echo "setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances" 

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"


echo "setup rule allowing SSH access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr $MY_IP/32

echo "setup rule allowing HTTP (port 5000) access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 5000 --protocol tcp \
    --cidr $MY_IP/32

UBUNTU_20_04_AMI="ami-042e8287309f5df03"


##############################################

# Creating the first instance

echo "Creating Ubuntu 20.04, first instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t3.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

FIRST_INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $FIRST_INSTANCE_ID

FIRST_PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $FIRST_INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $FIRST_INSTANCE_ID @ $FIRST_PUBLIC_IP"


# Creating the second instance

echo "Creating Ubuntu 20.04, second instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t3.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

SECOND_INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $SECOND_INSTANCE_ID

SECOND_PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $SECOND_INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $SECOND_INSTANCE_ID @ $SECOND_PUBLIC_IP"

##############################################

echo "deploying code to production"
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" $PYTHON_FILE_NAME ubuntu@$FIRST_PUBLIC_IP:/home/ubuntu/
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" $PYTHON_FILE_NAME ubuntu@$SECOND_PUBLIC_IP:/home/ubuntu/

##############################################

echo "setup production environment"

ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$FIRST_PUBLIC_IP <<EOF
    sudo apt update
    sudo apt install python3-flask -y
    sudo apt install python3-pip -y
    pip install boto3
    pip install requests
    # run app
    nohup flask run --host 0.0.0.0 > output.txt 2>&1 &
    exit
EOF

ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$SECOND_PUBLIC_IP <<EOF
    sudo apt update
    sudo apt install python3-flask -y
    sudo apt install python3-pip -y
    pip install boto3
    pip install requests
    # run app
    nohup flask run --host 0.0.0.0 > output.txt 2>&1 &
    exit
EOF

##############################################

echo "update python code with necessary information"

curl -X POST "http://${FIRST_PUBLIC_IP}:5000/updateIps?thisNodeIp=${FIRST_PUBLIC_IP}&otherNodeIp=${SECOND_PUBLIC_IP}"
curl -X POST "http://${SECOND_PUBLIC_IP}:5000/updateIps?thisNodeIp=${SECOND_PUBLIC_IP}&otherNodeIp=${FIRST_PUBLIC_IP}"

curl -X POST "http://${SECOND_PUBLIC_IP}:5000/setSecondNode"

curl -X POST "http://${FIRST_PUBLIC_IP}:5000/startTimer"
curl -X POST "http://${SECOND_PUBLIC_IP}:5000/startTimer"

##############################################


echo
echo
echo
echo
echo
echo
echo "_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_"
echo
echo "Machines successfully created."
echo
echo "Public IP of the first machine: ${FIRST_PUBLIC_IP}"
echo "Public IP of the second machine: ${SECOND_PUBLIC_IP}"
echo
echo "You can now send these requests to use the app:"
echo "curl -X PUT -H \"Content-Type: text/plain\" -d \"<Data to be hashed>\" \"http://<Public IP>:5000/enqueue?iterations=<Iterations>\""
echo "curl -X POST \"http://<Public IP>:5000/pullCompleted?top=<Number of results to return>\""
echo "curl -X POST \"http://<Public IP>:5000/debug\""
echo
echo "For example:"
echo "curl -X PUT -H \"Content-Type: text/plain\" -d \"Sample data\" \"http://${FIRST_PUBLIC_IP}:5000/enqueue?iterations=5\""
echo "curl -X POST \"http://${SECOND_PUBLIC_IP}:5000/pullCompleted?top=3\""
echo "curl -X POST \"http://${FIRST_PUBLIC_IP}:5000/debug\""
echo "curl -X POST \"http://${SECOND_PUBLIC_IP}:5000/debug\""
echo
echo "-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-"
echo
echo
