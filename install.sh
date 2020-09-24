#!/bin/bash

# get docker-compose yml
#wget https://trainingdataio.s3.amazonaws.com/docker-compose.ngx.yml
# pull trainingdata.io docker image
# docker pull trainingdataio/tdviewer:v2.0-ngx

curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey |   sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list |   sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get install nvidia-docker2

# pull nvidia docker image
docker pull nvcr.io/nvidia/clara-train-sdk:v3.0   

sudo apt-get install -y python3-pip

pip3 install -r flaskserver/requirements.txt
