# tdioinferenceserver

# Architecture 1: Local Annotation Servers & (separate) Inference Server 
![Architecture 1](https://github.com/trainingdata/tdioinferenceserver/blob/master/documentation/static/images/Architecture1.png)

# Architecture 2: Local (combined) Annotation & Inference Server
![Architecture 2](https://github.com/trainingdata/tdioinferenceserver/blob/master/documentation/static/images/Architecture2.png)

# Architecture 3: Cloud Annotation Server & Inference Server
![Architecture 3](https://github.com/trainingdata/tdioinferenceserver/blob/master/documentation/static/images/Architecture3.png)


## Download inference server from Github.com
```
git clone https://www.github.com/trainingdata/tdioinferenceserver
cd tdioinferenceserver
```

## Download models for medical imaging
```
git submodule update  --init --recursive
cd nvidiaclara
git lfs install
git lfs pull
cd ..
```

## Install & Run
```
./install.sh
./start.sh
```

## Stop server
```
./stop.sh
```
## Add ML Model to "ML Models Library"
## Create a Labeling Job
As shown in this video https://youtu.be/cjiNQ9DCtLo:
1. Create a labeling job with AI-Assisted annotation.
2. After manually cleaning AI-assisted annotations, launch re-train ML Model
