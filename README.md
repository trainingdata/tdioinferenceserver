# tdioinferenceserver

# Architecture 1: Local Inference Server
![Architecture 1](https://github.com/trainingdata/tdioinferenceserver/blob/master/documentation/static/images/Architecture1.png)

# Architecture 2: Local Inference Server
![Architecture 2](https://github.com/trainingdata/tdioinferenceserver/blob/master/documentation/static/images/Architecture2.png)

# Architecture 3: Local Inference Server
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
