# tdioinferenceserver
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
./install.sh
./start.sh
```

## Stop server
```
./stop.sh
```
