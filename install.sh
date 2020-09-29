#!/bin/bash

# get docker-compose yml
#wget https://trainingdataio.s3.amazonaws.com/docker-compose.ngx.yml
# pull trainingdata.io docker image
# docker pull trainingdataio/tdviewer:v2.0-ngx

# update submodule for medical imaging
git submodule update  --init --recursive

# install git lfs
sudo apt-get update && sudo apt-get install -y git-lfs

# download nvidiaclara models
cd nvidiaclara && git lfs pull && cd ..

# configure nvidia-docker2
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey |   sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list |   sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo service docker restart

# pull nvidia docker image
docker pull nvcr.io/nvidia/clara-train-sdk:v3.0   

# prepare light web server
sudo apt-get install -y python3-pip
pip3 install -r flaskserver/requirements.txt
