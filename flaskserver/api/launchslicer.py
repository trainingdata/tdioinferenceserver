import os
import json
import time
import requests
import uuid
from .fileio import downloadResourceFolder
from .utils import homeBaseGet, homeBasePost, homeBasePut, saveInferenceStatus, open3dSlicerWithMasterSegmentationVolumes, convertDicomDirectoryToNifti


def get(auth_token, taskid, jobid, useremail) -> dict:
   print(taskid, jobid)
   response = homeBaseGet(auth_token, '/task/' + str(taskid))
   task = json.loads(response)
   print(task)
   taskurl = task['path']
   splithost = taskurl.split('?')
   print(splithost)
   spliturl = (','.join((','.join(taskurl.split('='))).split('&'))).split(',')
   print(spliturl)
   jobid = spliturl[len(spliturl) - 1]
   print('jobid', jobid)

   response = homeBaseGet(auth_token, '/task/' + str(taskid) + '/job/' + str(jobid))
   projectjobjson = json.loads(response)
#    print('projectjobjson', projectjobjson)
   launchSlicer(auth_token, taskid, jobid, projectjobjson, useremail)

################# inference ###########

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
      retval = json.loads(response)
    except Exception as ex:
      print('Fatal error:', str(ex))
      status = False
      reason = str(ex)

    return (status, reason, retval)

def hexa2rgba(hexstr, opacity):
    rgba = 'rgba({},{},{},{})'.format(int(hexstr[-6:-4], 16), int(hexstr[-4:-2], 16),int(hexstr[-2:], 16),opacity)
    return rgba

def convertCornerstoneAnnotations(auth_token, seriesjson, results, labelinginterface, jobid):
    # iterate over tool
    if 'tools' in labelinginterface and len(labelinginterface['tools']) > 0:
        tool = labelinginterface['tools'][0]
    else:
        return
    # iterate over results
    instanceindex = -1
    results = list(reversed(results))
    for instance in seriesjson['instanceList']:
        instanceindex = instanceindex + 1
        instanceid = instance['instanceId']
        if len(results) < instanceindex+1:
            return
        image = results[instanceindex]
        tooldatas = []
        for polygon in image:
            # print(polygon)
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
                #print(vertex)
                if (lastindex >= 0):
                    tooldata['handles'][lastindex]['lines'].append({'x':vertex[1], 'y':512-vertex[0]})
                tooldata['handles'].append({'x': vertex[1], 'y':512-vertex[0], 'highlight':True, 'active':True, 'lines':[]});
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
        response = homeBaseGet(auth_token, '/cornerstoneannotation', queryparams={'job': jobid, 'instanceId':instanceid, 'seriesId':seriesjson['seriesId'], 'annotator':'auto@trainingdata.io'})
        cannotations = []
        cannotations = json.loads(response)
        print(jobid, instanceid, seriesjson['seriesId'], cannotations)
        if len(cannotations) == 0 or not cannotations[0]['jsonstring'] or cannotations[0]['jsonstring'] == None or cannotations[0]['jsonstring'] == '':
            existingannotations = {'annotations': [], 'stats':[], 'imageAttributes':[], 'lastmodified':int(time.time()), 'labelCount':len(tooldatas), 'reviews':[], 'width':512, 'height':512}
            cannotations.append({'job':jobid, 'instanceId':instanceid, 'seriesId':seriesjson['seriesId']})
        else:
            existingannotations = json.loads(cannotations[0]['jsonstring'])

        existingannotations['annotations'].append(annotation)
        cannotations[0]['jsonstring'] = json.dumps(existingannotations, ensure_ascii=False)
        cannotations[0]['annotator'] = 'auto@trainingdata.io'
        if 'id' in cannotations[0]:
            response = homeBasePut(auth_token, '/cornerstoneannotation/' + str(cannotations[0]['id']), json.dumps(cannotations[0], ensure_ascii=False))
        else:
            response = homeBasePost(auth_token, '/cornerstoneannotation', json.dumps(cannotations[0], ensure_ascii=False))
        print(response)

def cornerstoneannotationsToSlicerSegments():
    print('cornerstoneannotationsToSlicerSegments()')

def launchSlicer(auth_token, taskid, jobid, projectjobjson, useremail):
    # status
    status = True
    reason = ''

    # iterate over images and download them
    for series in projectjobjson['images']['seriesList']:
        imageIds = []
        targetfilepaths = []
        for instance in series['instanceList']:
            imageid = instance['imageId']
            folder = os.path.dirname(imageid)
            folder = os.path.basename(folder)
            workingdir = os.path.join('/tmp/', "data")
            workingdirpath = os.path.join(workingdir, folder)
            if not os.path.exists(workingdirpath):
                os.makedirs(workingdirpath)
            filename = os.path.basename(imageid).split('?')[0]
            filepart, extension = os.path.splitext(filename)
            if not 'dcm' in extension.lower():
               continue
            if 'dicomweb' in imageid:
               imageid = imageid.replace('dicomweb', 'http')
            imageIds.append(imageid)
            targetfilepaths.append(os.path.join(workingdirpath, filename))
        if len(imageIds) <= 0:
           print('Warning: no dcm files found in series:', series['seriesId'])
           continue

        newfiles = downloadResourceFolder(imageIds, targetfilepaths)
        newdir = str(uuid.uuid4())
        masterVolumeDir = os.path.join('/tmp', newdir)
        os.makedirs(masterVolumeDir)
        masterVolumeNiftiFile = os.path.join(masterVolumeDir, newdir+'.nii.gz')
        convertDicomDirectoryToNifti(workingdirpath, masterVolumeNiftiFile)

        # launch slicer with master volume and segmentation volume
        open3dSlicerWithMasterSegmentationVolumes({'jobid':jobid, 'authtoken': auth_token, 'useremail':useremail, 'projectjson': projectjobjson}, masterVolumeNiftiFile, None)
        break