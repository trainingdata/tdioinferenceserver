#!/bin/bash

CONTAINERID=`docker ps -aqf 'name=nvidiaclara'`

echo stopping Docker containerid ... ${CONTAINERID}
docker stop ${CONTAINERID}
