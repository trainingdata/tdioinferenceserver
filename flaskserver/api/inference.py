import os
import json
import time
import requests
import uuid
import traceback
import nibabel as nib
import numpy as np
from .fileio import downloadResourceFolder
from .utils import homeBaseGet, homeBasePost, homeBasePut, saveInferenceStatus, open3dSlicerWithMasterSegmentationVolumes
from . import autoannotation
from .nvidiaclaraannotation import inferenceOnNumpy2D, inferenceOnNiftiVolume

try:
    # Python3
    # noinspection PyUnresolvedReferences
    import http.client as httplib
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.parse import quote_plus
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.parse import urlparse
except ImportError as e:
    # Python2
    # noinspection PyUnresolvedReferences
    import httplib
    # noinspection PyUnresolvedReferences
    from urllib import quote_plus
    # noinspection PyUnresolvedReferences
    from urlparse import urlparse

def get(auth_token, taskid, jobid, mlmodelid) -> dict:
#    taskid = inferencedata['taskid'][0]
#    jobid = inferencedata['jobid'][0]
#    mlmodelid = inferencedata['mlmodelid'][0]
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
   if mlmodel['modeltype'] == 'nvidiaclara' :
       saveInferenceStatus(auth_token, taskid, 'queued', 'queued', '', int(time.time()), "NA")
       return runInference(auth_token, taskid, jobid, projectjobjson, mlmodel)
   else :
       labelling_interface = homeBaseGet(auth_token, '/labelinterfacetemplates/' + str(task["labeling_interface"]))
       labelling_interface = json.loads(labelling_interface)
       labelling_interface['jsonstring'] = json.loads(labelling_interface['jsonstring'])
       return autoannotation.start_autoannotation(task, mlmodel, projectjobjson, jobid, labelling_interface, auth_token)

################# inference ###########

def microserviceNvidiaClaraSegmentation2(directorypath, aiserver, aimodel):
    return inferenceOnNiftiVolume(directorypath, '', aiserver, aimodel)
    
def microserviceNvidiaClaraSegmentation(directorypath, aiserver, aimodel):
    status = True
    url = 'http://localhost:9090/v1/nvidiaclarasegmentation'
    headers = {
        'content-type': "application/x-www-form-urlencoded"
    }
    payload = {'directorypath': directorypath, 'seriesjson':'', 'aiserver':aiserver, 'aimodel':aimodel}

    retval = ''
    reason = ''
    try:
      response = requests.request("POST", url, data=payload, headers=headers)
      retval = response.json()
    except Exception as ex:
      print('Fatal error:', str(ex))
      status = False
      reason = str(ex)

    return (status, reason, retval)

def hexa2rgba(hexstr, opacity):
    rgba = 'rgba({},{},{},{})'.format(int(hexstr[-6:-4], 16), int(hexstr[-4:-2], 16),int(hexstr[-2:], 16),opacity)
    return rgba

def convertCornerstoneAnnotationsInstance(auth_token, jobid, contours, tool, seriesid, instanceid, width, height):
        tooldatas = []
        for polygon in contours:
            # print('polygon', polygon)
            tooldata = {'id': str(uuid.uuid4()),
                    'visible': True,
                    'active': False,
                    'alwaysActive': True,
                    'canComplete': False,
                    'invalidated': True,
                    'highlight': False,
                    'selectedClass': tool['name'],
                    'color': tool['color'],
                    'fillColor': hexa2rgba(tool['color'], 0.3),
                    'fillStyle': hexa2rgba(tool['color'], 0.3),
                    'textBox': {'active': False, 'allowOutsideImage': True, 'drawnIndependently': True, 'hasBoundingBox': True, 'hasMoved': False, 'movesIndependently': False},
                    'handles': []}
            lastindex = -1
            for vertex in polygon:
                # print(vertex)
                if (lastindex >= 0):
                    tooldata['handles'][lastindex]['lines'].append({'x':vertex[1], 'y':height-vertex[0]})
                tooldata['handles'].append({'x': vertex[1], 'y':width-vertex[0], 'highlight':True, 'active':True, 'lines':[]});
                lastindex = lastindex + 1
            tooldatas.append(tooldata)
        annotation = {
                    'id': str(uuid.uuid4()),
                    'annotationClass': tool['name'],
                    'annotationName': '',
                    'selectedColor': tool['color'],
                    'toolName': 'freehand',
                    'toolData': tooldatas,
                    'toolDataIndex': 0,
                    'annotatedOn': int(time.time()),
                    'classAttributes': {},
                    'useremail': 'auto@trainingdata.io'
                  }
        response = homeBaseGet(auth_token, '/cornerstoneannotation', queryparams={'job': jobid, 'instanceId':instanceid, 'seriesId':seriesid, 'annotator':'auto@trainingdata.io'})
        cannotations = []
        cannotations = json.loads(response)
        # print(jobid, instanceid, seriesjson['seriesId'], cannotations)
        if len(cannotations) == 0 or not cannotations[0]['jsonstring'] or cannotations[0]['jsonstring'] == None or cannotations[0]['jsonstring'] == '':
            existingannotations = {'annotations': [], 'stats':[], 'imageAttributes':[], 'lastmodified':int(time.time()), 'labelCount':len(tooldatas), 'reviews':[], 'width':width, 'height':height}
            cannotations.append({'job':jobid, 'instanceId':instanceid, 'seriesId':seriesid})
        else:
            existingannotations = json.loads(cannotations[0]['jsonstring'])

        existingannotations['annotations'].append(annotation)
        cannotations[0]['jsonstring'] = json.dumps(existingannotations, ensure_ascii=False)
        cannotations[0]['annotator'] = 'auto@trainingdata.io'
        if 'id' in cannotations[0]:
            response = homeBasePut(auth_token, '/cornerstoneannotation/' + str(cannotations[0]['id']), json.dumps(cannotations[0], ensure_ascii=False))
        else:
            response = homeBasePost(auth_token, '/cornerstoneannotation', json.dumps(cannotations[0], ensure_ascii=False))
    
def convertCornerstoneAnnotationsSeries(auth_token, seriesjson, results, matchingtool, jobid, width, height):
    # iterate over results
    instanceindex = -1
    results = list(reversed(results))
    results = results[2:]
    for instance in seriesjson['instanceList']:
        instanceindex = instanceindex + 1
        instanceid = instance['instanceId']
        if len(results) < instanceindex+1:
            return
        contoursforimage = results[instanceindex]

        convertCornerstoneAnnotationsInstance(auth_token, jobid, contoursforimage, matchingtool, seriesjson['seriesId'], instanceid, width, height)
        #print(response)

def convertCornerstoneAnnotationsSeriesNiftiVolume(auth_token, seriesjson, niftifilepath, labelinginterface, jobid, tools):
    # iterate over images in niftivolume
    seriesjson['instanceList'] = sorted(seriesjson['instanceList'], key = lambda i: i['imageId'], reverse=True)
    img = nib.load(niftifilepath)
    data = img.get_fdata()
    width = data.shape[2]
    height = data.shape[1]
    data1 = np.transpose(data, (2,0,1))
    for instance, image in zip(seriesjson['instanceList'], data1):
        instanceid = instance['instanceId']
        convertCornerstoneAnnotationsInstanceNifti(auth_token, jobid, image, tools, seriesjson['seriesId'], instanceid, width, height)

def convertCornerstoneAnnotationsSeriesDicomVolume(auth_token, seriesjson, niftifilepath, labelinginterface, db_job, tools):
    # iterate over images in niftivolume
    seriesjson['instanceList'] = sorted(seriesjson['instanceList'], key = lambda i: i['imageId'], reverse=True)
    img = nib.load(niftifilepath)
    data = img.get_fdata()
    width = data.shape[2]
    height = data.shape[1]
    data1 = np.transpose(data, (2,0,1))
    for instance, image in zip(seriesjson['instanceList'], data1):
        instanceid = instance['instanceId']
        convertCornerstoneAnnotationsInstanceNifti(auth_token, jobid, image, tools, seriesjson['seriesId'], instanceid, width, height)

def convertCornerstoneAnnotationsInstanceNifti(auth_token, jobid, niftiimage, tools, seriesid, instanceid, width, height, inputlabel=-1):
    try:
        labelmap = {}
        labelmap = niftiImage2Labels(niftiimage, labelmap, inputlabel)

        newannotations= []
        for label in labelmap:
            if label == 0:
              if inputlabel != -1:
                # ignore 0
                continue
              else:
                tool = {'name':'__inverse__', 'color':'#7e7e7e'}
            else:
              tool = tools[label]
            vertexmap = labelmap[label]
            
            tooldatas = []
            tooldata = {'id': str(uuid.uuid4()),
                'visible': True,
                'active': False,
                'alwaysActive': True,
                'selectedClass': tool['name'],
                'color': tool['color'],
                'fillColor': hexa2rgba(tool['color'], 0.3),
                'fillStyle': hexa2rgba(tool['color'], 0.3),
                'data': []}
            tooldata['data'] = vertexmap   
            tooldatas.append(tooldata)
            annotation = {
                    'id': str(uuid.uuid4()),
                    'annotationClass': tool['name'],
                    'annotationName': '',
                    'selectedColor': tool['color'],
                    'toolName': '2dgrowthtool',
                    'toolData': tooldatas,
                    'toolDataIndex': 0,
                    'annotatedOn': int(time.time()),
                    'classAttributes': {},
                    'useremail': 'auto@trainingdata.io'
            }
            newannotations.append(annotation)
        if len(newannotations) == 0:
            return
        response = homeBaseGet(auth_token, '/cornerstoneannotation', queryparams={'job': jobid, 'instanceId':instanceid, 'seriesId':seriesid, 'annotator':'auto@trainingdata.io'})
        cannotations = []
        cannotations = json.loads(response)
        # print(jobid, instanceid, seriesjson['seriesId'], cannotations)
        if len(cannotations) == 0 or not cannotations[0]['jsonstring'] or cannotations[0]['jsonstring'] == None or cannotations[0]['jsonstring'] == '':
            existingannotations = {'annotations': [], 'stats':[], 'imageAttributes':[], 'lastmodified':int(time.time()), 'labelCount':len(tooldatas), 'reviews':[], 'width':width, 'height':height}
            cannotations.append({'job':jobid, 'instanceId':instanceid, 'seriesId':seriesid})
        else:
            existingannotations = json.loads(cannotations[0]['jsonstring'])

        existingannotations['annotations'] = newannotations
        cannotations[0]['jsonstring'] = json.dumps(existingannotations, ensure_ascii=False)
        cannotations[0]['annotator'] = 'auto@trainingdata.io'
        if 'id' in cannotations[0]:
            response = homeBasePut(auth_token, '/cornerstoneannotation/' + str(cannotations[0]['id']), json.dumps(cannotations[0], ensure_ascii=False))
        else:
            response = homeBasePost(auth_token, '/cornerstoneannotation', json.dumps(cannotations[0], ensure_ascii=False))
    except Exception as ex:
        traceback.print_exc()

def niftiImage2Labels(npniftiimage, labelmap, inputlabel=-1): 
   try:
    # print(npniftiimage.shape)
    width = npniftiimage.shape[1]
    height = npniftiimage.shape[0]
    minmaxx = []
    p = []
    for x in range(len(npniftiimage)):
      minmaxx.append([])
      minmaxx[x] = []
      for y in range(len(npniftiimage[x])):
        label = int(npniftiimage[x][y])
        xx = x
        if inputlabel != -1 and label != 0:
          label = inputlabel
        #if label != 0:
        #    print('xy', x, y, label)
        # calculate minmaxx of this column
        if label == 0 and (len(minmaxx) == 0) and (x-1 > 0 and len(minmaxx[x-1]) == 0):
          continue
        if label != 0 and len(minmaxx[x]) == 0:
          minmaxx[x].append(y)
          minmaxx[x].append(y)
        elif label != 0 and minmaxx[x][1] < y:
          minmaxx[x][1] = y
        # create space in p  
        if label >= len(p):
         #print(label, len(p))
         for i in range(len(p), label+1):
          p.append([])
        # create space in p[label]
        if x >= len(p[label]):
          for i in range(len(p[label]), xx+1):
            p[label].append([])
        # insert in p[label][x] 
        if (len(minmaxx[x]) > 0):
          # print('append', label, x, y)
          p[label][xx].append(height-y)
        elif (x-1 >= 0) and (len(minmaxx[x-1]) > 0) and (y > minmaxx[x-1][0]) and (y < minmaxx[x-1][1]):
          # print('append', label, x, y)
          p[label][xx].append(height-y)

      # print (p[0], minmaxx[x])
      # trim the p[0][x] from the end
      if len(minmaxx[x]) > 0:
        for i in range(len(p[0][xx]) - 1, 0, -1):
          if (height-p[0][xx][i]) > minmaxx[x][1]:
              p[0][xx] = p[0][xx][:-1]

      # if len(minmaxx[x]) == 0:
      #    minmaxx[x] = minmaxx[x-1]

    for l in range(len(p)):
       if len(p[l]) > 0:
           labelmap[l] = p[l]
   except Exception as ex:
    print('niftiImage2Labels:', str(ex))
    traceback.print_exc()

   return labelmap
        
def runInference(auth_token, taskid, jobid, projectjobjson, tdmlmodel):
    saveInferenceStatus(auth_token, taskid, 'running', 'running', '', int(time.time()), "NA")
    # status
    status = 'running'
    reason = ''

    # matching tool
    # matchingtool = projectjobjson['labelinginterface']['tools'][0]
    labelinginterface = projectjobjson['labelinginterface']
    print(tdmlmodel['jsonconfig'], labelinginterface)
    tdmlmodel['jsonconfig'] = json.loads(tdmlmodel['jsonconfig'])
    # iterate over tool
    labelindex = 0
    matchingtool = {}
    try:
      labelsinmlmodel = tdmlmodel['jsonconfig']['labels']
      if 'tools' in labelinginterface and len(labelinginterface['tools']) > 0:
        for label in labelsinmlmodel:
         for tool in labelinginterface['tools']:
          print(label, tool['name'])
          if tool['name'].strip().lower() == label.strip().lower():
            matchingtool[labelindex+1] = tool
            break
         labelindex = labelindex + 1
      else:
        return 'No Tools Found', 400
    except Exception as ex:
      saveInferenceStatus(auth_token, taskid, 'error', 'error', ex, int(time.time()), "NA")
      print('runClaraInference:error:', ex)
      traceback.print_exc()
      return 'No Labels / Tools Found', 400

    print('matchingtool', matchingtool)
    # mlmodel input output
    mlmodelinput = tdmlmodel['jsonconfig']['inputfiletype']
    mlmodeloutput = tdmlmodel['jsonconfig']['outputfiletype']
    mlmodelinputwidth = 320
    mlmodelinputheight = 320
    if 'inputdims' in tdmlmodel['jsonconfig']:
      mlmodelinputwidth = tdmlmodel['jsonconfig']['inputdims']['width']
      mlmodelinputheight = tdmlmodel['jsonconfig']['inputdims']['height']

    # iterate over images and download them
    try:
      for series in projectjobjson['images']['seriesList']:
        imageIds = []
        targetfilepaths = []
        for instance in series['instanceList']:
            imageid = instance['imageId']
            instanceid = instance['instanceId']
            folder = os.path.dirname(imageid)
            folder = os.path.basename(folder)
            workingdir = os.path.join('/tmp/', "data")
            workingdirpath = os.path.join(workingdir, folder)
            if not os.path.exists(workingdirpath):
                os.makedirs(workingdirpath)
            filename = os.path.basename(imageid).split('?')[0]
            filepart, extension = os.path.splitext(filename)
            if not 'dcm' in mlmodelinput.lower() and not '.nii' in mlmodelinput.lower():
                # numpy, or jpeg, or png
                print('downloadResourceFolder', imageid)
                newfiles = downloadResourceFolder([imageid], [os.path.join(workingdirpath, filename)])
                niftifilepaths = inferenceOnNumpy2D(newfiles[0], instanceid, tdmlmodel['serverurl'], tdmlmodel['jsonconfig']['identifier'], mlmodelinputwidth, mlmodelinputheight)
                if len(niftifilepaths) <= 0:
                    continue
                # convertCornerstoneAnnotationsInstance(auth_token, jobid, contours, matchingtool, series['seriesId'], instanceid, width, height) 
                # iterate over images in niftivolume
                img = nib.load(niftifilepaths[0])
                data = img.get_fdata()
                width = data.shape[1]
                height = data.shape[0]
                convertCornerstoneAnnotationsInstanceNifti(auth_token, jobid, data, matchingtool, series['seriesId'], instanceid, width, height)
                status = 'finished'
            else:
                imageIds.append(imageid)
                targetfilepaths.append(os.path.join(workingdirpath, filename))
            if 'dicomweb' in imageid:
               imageid = imageid.replace('dicomweb', 'http')

        if len(imageIds) <= 0:
           print('Warning: no dcm files found in series:', series['seriesId'])
           continue
        else:
            # dcm or nifti
            newfiles = downloadResourceFolder(imageIds, targetfilepaths)
            # call microservice to do inference
            outputniftifilepaths = microserviceNvidiaClaraSegmentation2(workingdirpath, tdmlmodel['serverurl'], tdmlmodel['jsonconfig']['identifier'])

            # check status of results
            if len(outputnitfifilepaths) > 0:
                # iterate results and convert to cornerstoneannotations for the task
                # print(results)
              if len(newfiles) == 1 and '.nii' in newfiles[0]:
                convertCornerstoneAnnotationsSeriesNiftiVolume(auth_token, series, outputniftifilepaths[0], labelinginterface, jobid, matchingtool)
              else:
                convertCornerstoneAnnotationsSeriesDicomVolume(series, niftioutputfilepath, projectjobjson['labelinginterface'], db_job, matchingtool)
                # convertCornerstoneAnnotationsSeries(auth_token, series, results, matchingtool, jobid, width, height)
                status = 'finished'
            else:
                status = 'failed'
                break
    except Exception as ex:
      print(str(ex))
      return str(ex), 400
    # save inferencestate
    saveInferenceStatus(auth_token, taskid, status, 'finished', '', int(time.time()), "NA")
    return 'Success', 200

def rgb2gray(rgb):
  r = (rgb >> 16)
  g = 0x00ff & (rgb >> 8)
  b = 0x0000ff & rgb
  print(r, g ,b)
  g = (0.2989 * r) + (0.5870 * g) + (0.1140 * b)
  print(g)
