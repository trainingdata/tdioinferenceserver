#!/bin/bash

PWD=`pwd`
HOME_DIR=$HOME
WORKSPACE_DIR=$HOME_DIR/workspace/trainingdataio
SAMPLES_DIR=$WORKSPACE_DIR/samples
KNEE_MODEL=knee
VERTEBRA_MODEL=vertebra
MMARS_DIR=$PWD/nvidiaclara/mmars
echo "MMARS directory...$MMARS_DIR"
echo "Workspace directory...$WORKSPACE_DIR"
echo "Sample directory...$SAMPLES_DIR"
KNEE_MODEL=knee2d
VERTEBRA_MODEL=vertebra2d
COVID19_GGOMODEL=covid19/trainingdataio_covid19_ct_lung_seg_v1
CONTAINER_AIAA_DIR=/var/nvidia/aiaa
CONTAINER_AIAA_MMAR_DIR=$CONTAINER_AIAA_DIR/mmars
CONTAINER_AIAA_SAMPLES_DIR=$CONTAINER_AIAA_DIR/samples

# check directories
if [ ! -d "$WORKSPACE_DIR" ]; then
    # exit
    echo "workspace directory not found: ${WORKSPACE_DIR}"
    mkdir -p $WORKSPACE_DIR
fi

if [ ! -d "$MMARS_DIR" ]; then
    # exit
    echo "mmars directory not found: ${MMARS_DIR}"
    exit
fi

USER=`id -u --name`
GROUP=`id -g --name`
echo "USER=$USER,GROUP=$GROUP"
sudo chown -R $USER:$GROUP $WORKSPACE_DIR
sudo chmod -R a+w $WORKSPACE_DIR
sudo chmod -R a+r $WORKSPACE_DIR
sudo chown -R $USER:$GROUP $MMARS_DIR
sudo chmod -R a+w $MMARS_DIR
sudo chmod -R a+r $MMARS_DIR

KNEE_DIR=$MMARS_DIR/$KNEE_MODEL
VERTEBRA_DIR=$MMARS_DIR/$VERTEBRA_MODEL
COVID19_DIR=$MMARS_DIR/$COVID19_GGOMODEL

if [ ! -d "$KNEE_DIR" ]; then
    # exit
    echo "KNEE directory not found: ${KNEE_DIR}"
    exit
fi
if [ ! -d "$VERTEBRA_DIR" ]; then
    # exit
    echo "VERTEBRA directory not found: ${VERTEBRA_DIR}"
    exit
fi
if [ ! -d "$COVID19_DIR" ]; then
    # exit
    echo "COVID19 directory not found: ${COVID19_DIR}"
    exit
fi

#export PARENTHOST=$(ifconfig | grep -E "([0-9]{1,3}\.){3}[0-9]{1,3}" | grep -v 127.0.0.1 | awk '{ print $2 }' | cut -f2 -d: | head -n1)
#export DB_MOUNT=/tmp && export IMAGE_MOUNT=/home/user/images && docker-compose -f docker-compose.ngx.yml up -d

CONTAINERID=`docker run -d --name=nvidiaclara --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=0 --shm-size=6g --ulimit memlock=-1 --ulimit stack=67108864 -it --rm  -p 5000:80 -v $MMARS_DIR:$CONTAINER_AIAA_MMAR_DIR -v $MMARS_DIR:/workspace/mmars -v $SAMPLES_DIR:$CONTAINER_AIAA_SAMPLES_DIR nvcr.io/nvidia/clara-train-sdk:v3.0 start_aas.sh --debug 1`

echo starting ... ${CONTAINERID}
countdown=12
while [ $countdown -gt 0 ]
  do
    sleep 5
    countdown=$(($countdown-1))
    echo '.......'
  done
echo started ... ${CONTAINERID}

echo "USER=$USER,GROUP=$GROUP"
sudo chown -R $USER:$GROUP $WORKSPACE_DIR
sudo chmod -R a+w $WORKSPACE_DIR
sudo chmod -R a+r $WORKSPACE_DIR
sudo chown -R $USER:$GROUP $MMARS_DIR
sudo chmod -R a+w $MMARS_DIR
sudo chmod -R a+r $MMARS_DIR

docker cp $KNEE_DIR/CustomTransformations-aiaa.py $CONTAINERID:/var/nvidia/aiaa/transforms/
docker cp $KNEE_DIR/CustomTransformations.py $CONTAINERID:/var/nvidia/aiaa/transforms/

echo 'Installing knee2d model...'
curl -X PUT "http://127.0.0.1:5000/admin/model/knee2d" -F "config=@${KNEE_DIR}/config/config_aiaa.json;type=application/json" -F "data=@${KNEE_DIR}/models/model.zip"
sleep 5
curl -X PUT "http://127.0.0.1:5000/admin/model/knee2d" -F "config=@${KNEE_DIR}/config/config_aiaa.json;type=application/json" -F "data=@${KNEE_DIR}/models/model.zip"

sleep 5
echo 'Installing vertebra2d model...'
curl -X PUT "http://127.0.0.1:5000/admin/model/vertebra2d" -F "config=@${VERTEBRA_DIR}/config/config_aiaa.json;type=application/json" -F "data=@${VERTEBRA_DIR}/models/model.zip"

#run flask server
python3 flaskserver/app.py &
