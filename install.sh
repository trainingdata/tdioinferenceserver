#!/bin/bash

# get docker-compose yml
#wget https://trainingdataio.s3.amazonaws.com/docker-compose.ngx.yml

# pull nvidia docker image
docker pull nvcr.io/nvidia/clara-train-sdk:v3.0   

sudo apt-get install -y python3-pip

pip3 install -r flaskserver/requirements.txt
# pull trainingdata.io docker image
# docker pull trainingdataio/tdviewer:v2.0-ngx
