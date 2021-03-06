import tarfile
import datetime
import json
import requests
from .fileio import downloadResourceFolder
from urllib.parse import unquote
import os
from .dicom import pydicom_to_npy, png_to_npy, generateBlackNumpyLabel
from .export import hex_to_rgb, exportMasks, getAllClasses, getFileName
import traceback
from .utils import homeBaseGet, homeBasePost, homeBasePut, saveInferenceStatus
import random
import math

DATASET_JSON_STR = '{  "description": "",  "label_format": [1],  "name": "",  "numTest": 0,  "numTraining": 0,  "test": [],  "training": [{}],  "validation": [{}]    }'
ENV_JSON_STR = '{{  "MMAR_ROOT": "/var/nvidia/aiaa/mmars/{}/",  "DATA_ROOT": "/var/nvidia/aiaa/samples/",  "DATASET_JSON": "/var/nvidia/aiaa/samples/{}/dataset.json",  "PROCESSING_TASK": "segmentation",  "MMAR_CKPT_DIR": "/var/nvidia/aiaa/mmars/{}/models/{}",  "MMAR_CKPT":"/var/nvidia/aiaa/mmars/{}/models/{}/model_final.ckpt"}}'
def rgb2gray(rgb):
  r, g, b = hex_to_rgb(rgb)
  #r = (rgb >> 16)
  #g = 0x00ff & (rgb >> 8)
  #b = 0x0000ff & rgb
  print(r, g ,b)
  g = (0.2989 * r) + (0.5870 * g) + (0.1140 * b)
  return int(g)

def getLabelMap(labelinginterface):
    labelmap = {0:0}
    allcolors = []
    try:
      if 'tools' in labelinginterface and len(labelinginterface['tools']) > 0:
         for tool in labelinginterface['tools']:
          if tool['tool'].lower() == 'segmentation':
            g = rgb2gray(tool['color'])
            allcolors.append(g)
         allcolors.sort()
         index = 1      
         for c in allcolors:
           labelmap[c] = index
           index = index + 1
      else:
        return
    except Exception as ex:
      print('getLabelMap error:', ex)
      traceback.print_exc()
      return

    print('getLabelMap():', labelmap)
    return labelmap

def writeEnvDatasetJson(output_dir, newlabeleddataset, mlmodelname, outputmodelversion, inputmodelversion, percenttest, percenttraining, percentvalidation):
    try:
      testset = []
      validationset = []
      trainingset = []
      print(newlabeleddataset, newlabeleddataset.keys())
      alllabels = list(newlabeleddataset.keys())
      print('here2', len(alllabels))
      numTest = math.floor((percenttest / 100) * len(alllabels))
      numTraining = math.floor((percenttraining / 100) * len(alllabels))
      numValidation = math.floor((percentvalidation / 100) * len(alllabels))
      print('here3', numTest, numTraining, numValidation)
      random.shuffle(alllabels)
      count = 0
      for label in alllabels:
        count = count + 1
        image = newlabeleddataset[label]
        print(count, 'label', label, 'image', image) 
        if count >= 0 and count <= numTest:
          testset.append(image)
          print('test:', count)
        if count > numTest and count <= numTest+numTraining:
          trainingset.append({'image': image, 'label':label})
          print('train:', count)
        if count > numTraining+numTest and count <= (numTest + numTraining + numValidation):
          validationset.append({'image': image, 'label':label})
          print('validation:', count)
      
      datasetjsonfilename = os.path.join(output_dir, 'dataset.json')
      datasetjson = json.loads(DATASET_JSON_STR)
      datasetjson['description'] = mlmodelname 
      datasetjson['name'] = mlmodelname
      datasetjson['numTest'] = numTest
      datasetjson['numTraining'] = numTraining
      datasetjson['numValidation'] = numValidation
      datasetjson['training'] = trainingset
      datasetjson['test'] = testset
      datasetjson['validation'] = validationset
      with open(datasetjsonfilename, 'w') as datasetjsonfile:
        datasetjsonfile.write(json.dumps(datasetjson, ensure_ascii=False, indent=4, separators=(',', ': ')))

      envconfigjson = ENV_JSON_STR.format(mlmodelname, mlmodelname, mlmodelname, outputmodelversion, mlmodelname, inputmodelversion)
      envconfigjsonfilename = os.path.join(output_dir, 'environment.json')
      with open(envconfigjsonfilename, 'w') as envjsonfile:
        envjsonfile.write(json.dumps(json.loads(envconfigjson), ensure_ascii=False, indent=4, separators=(',', ': ')))
        
    except Exception as ex:
        print('Failed to write dataset.json: {}'.format(str(ex)))
        raise ex
  
def get(auth_token, taskid, jobid, mlmodelid, annotatoremail, inputmodelversion, outputmodelversion, percenttraining, percenttest, percentvalidation):
  try:
    print(taskid, jobid, mlmodelid)
    response = homeBaseGet(auth_token, '/task/' + str(taskid))
    task = json.loads(response)
    print('response:', response, task)
    taskurl = task['path']
    splithost = taskurl.split('?')
    print(splithost)
    spliturl = (','.join((','.join(taskurl.split('='))).split('&'))).split(',')
    print(spliturl)
    jobid = spliturl[len(spliturl) - 1]
    print('jobid', jobid)

    response = homeBaseGet(auth_token, '/tdmlmodel/' + str(mlmodelid))
    mlmodel = json.loads(response)
    # print(mlmodel['jsonconfig'])
    # mlmodel['jsonconfig'] = json.loads(mlmodel['jsonconfig'])
    print('mlmodel', mlmodel, mlmodel['jsonconfig'])
    response = homeBaseGet(auth_token, '/task/' + str(taskid) + '/job/' + str(jobid))
    projectjobjson = json.loads(response)
    print('projectjobjson', projectjobjson)

    if not mlmodel or not (mlmodel['modeltype'] == 'nvidiaclara'):
        print("MlModel missing in the Task - /tdmlmodel/finetune")
        return "Invalid Request. Missing mlmodel", 400
    mlmodel['jsonconfig'] = json.loads(mlmodel['jsonconfig'])
    mlmodelname = mlmodel['jsonconfig']['identifier']
    # mlmodel input output
    mlmodelinput = mlmodel['jsonconfig']['inputfiletype']
    mlmodeloutput = mlmodel['jsonconfig']['outputfiletype']
    mlmodelinputwidth = 320
    mlmodelinputheight = 320
    if 'inputdims' in mlmodel['jsonconfig']:
      mlmodelinputwidth = mlmodel['jsonconfig']['inputdims']['width']
      mlmodelinputheight = mlmodel['jsonconfig']['inputdims']['height']

    workspace_dir = os.path.join('/workspace', taskid)
    output_dir = os.path.join(workspace_dir, 'samples', mlmodel['jsonconfig']['identifier'])
    retdir = []
    # create an archive (zip) of samples/<modelname>/{images+labels}
    classes = getAllClasses(projectjobjson['labelinginterface'])
    labelmap = getLabelMap(projectjobjson['labelinginterface'])
    retdir.append(os.path.join(workspace_dir, 'samples'))
    labelsdir = os.path.join(output_dir, 'labels')
    imagesdir = os.path.join(output_dir, 'images')
    if not os.path.exists(labelsdir):
      os.makedirs(labelsdir)
    if not os.path.exists(imagesdir):
      os.makedirs(imagesdir)
    # generate masks
    background_color = hex_to_rgb('#000000')
    mask_bitness = 24
    exportMasks(jobid, projectjobjson, classes, output_dir, background_color, mask_bitness, mask_dirname='labels', exclude_dirname=True)

    newlabeleddataset = {}
    imageCount = 0
    for series in projectjobjson['images']['seriesList']:
        for instance in series['instanceList']:
            imageCount += 1
            imageId = instance['imageId']
            # imageId = unquote(imageId)
            # filename, ext = getFileName(imageId.split('?')[0])
            filename, ext = os.path.splitext(imageId.split('?')[0])
            filename = os.path.basename(filename)
            targetfilepath = os.path.join(imagesdir, filename + ext)
            newfiles = downloadResourceFolder([imageId], [targetfilepath])
            if not os.path.exists(os.path.dirname(os.path.join(imagesdir, filename))):
              os.makedirs(os.path.dirname(os.path.join(imagesdir, filename)))
            print(newfiles)
            suffix = '-' + annotatoremail 
            labelfile = os.path.join(labelsdir, filename + suffix + ext)
            pnglabelfile = labelfile.replace(ext, '.png')
            npylabelfile = os.path.join(labelsdir, filename + '.npy')
            # npylabelfile = labelfile.replace(ext, '.npy')
            print(pnglabelfile, npylabelfile)
            if '.nii' in ext.lower():
                print('if')
                # data = getNiftiData(newfiles[0])
                # data = np.ndarray((data.shape()[1], data.shape()[2]), dtype=np.uint8)
                # assumen label = nii.gz
            elif ".dcm" in ext.lower():
                # if mlmodelinput == '.npy':
                  print('elif')
                  numpyfile = pydicom_to_npy(newfiles[0], mlmodelinputwidth, mlmodelinputheight)
                  newlabeleddataset[npylabelfile.split('samples/')[1]] = numpyfile.split('samples/')[1]
                  os.remove(newfiles[0])
                  if not os.path.exists(pnglabelfile):
                    print('generateBlackNumpyLabel', os.path.exists(pnglabelfile))
                    generateBlackNumpyLabel(npylabelfile, mlmodelinputwidth, mlmodelinputheight)
                  else:
                    png_to_npy(pnglabelfile, npylabelfile, mlmodelinputwidth, mlmodelinputheight, labelmap)
            else:
                print('else')
                png_to_npy(newfiles[0], npylabelfile, mlmodelinputwidth, mlmodelinputheight, labelmap)
                np.save(npylabelfile, data)

    # write dataset.json
    writeEnvDatasetJson(output_dir, newlabeleddataset, mlmodelname, outputmodelversion, inputmodelversion, percenttest, percenttraining, percentvalidation)
    
    # path to build archive
    archivename = str(taskid) + '-' + annotatoremail + '-' + str(datetime.datetime.now().date()) + '.tar.gz'
    os.chdir(workspace_dir)
    tar = tarfile.open(archivename, "w:gz")
    for d in retdir:
        tar.add(os.path.basename(d), arcname=os.path.basename(d))
    tar.close()

    #uploadedFile = uploadFileToS3(settings.AWS_STORAGE_BUCKET_NAME, os.path.join('export', str(task.id), str(datetime.datetime.now().date()), archivename), tar.name)
    url = os.path.join(mlmodel['serverurl'].replace('5000','9090'), 'v1/finetune')
    data = {}
    data['mlmodel'] = mlmodelname
    data['modelversion'] = outputmodelversion 
    files = {'archivefile':open(archivename, 'rb')}
    response = requests.post(url, data=data, files=files)
    if response.status_code != 200:
      status = "Failed finetunemodel {}".format(response.status_code)
      print(status)
      return status, 400
    else:
      status = response.text
  except Exception as ex:
    status = "Failed finetunemodel {}".format(ex)
    print(status)
    return status, 400
    
  return 'Success {}'.format(status), 200
