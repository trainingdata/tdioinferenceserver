import os
import requests
import subprocess
import dicom2nifti
from .TDIOClientAPI.client_api import TDIOUtils
import base64
import numpy as np
from PIL import Image
# from .s3_upload import createPresignedUrl

BASE_URL = 'https://app.trainingdata.io'
#BASE_URL = 'http://localhost:9080'
SLICER_DIR = 'slicerlatest'
SLICER_EXE = 'Slicer'
# PIPE = '/tmp/tdioslicerpipe'
PIPE = '/home/user/trainingdataio/tdviewer/images/tdioslicerpipe'

def homeBaseGet(auth_token, api, queryparams=None):
   url = os.path.join(BASE_URL + api)
   # jsonheaderup={'Authorization': 'Token ' + auth_token}
   # response = requests.get(url, params=queryparams, headers=jsonheaderup)
   first = True
   if queryparams:
      for key in queryparams:
         if first:
            first = False
            api = api + "?"
         else:
            api = api + "&"
         print(key, queryparams[key])
         api = api + key + "=" + TDIOUtils.urllib_quote_plus(str(queryparams[key]).encode('utf-8'))
   response = TDIOUtils.http_get_method(auth_token, BASE_URL, api)
   response = response.decode('utf-8') if isinstance(response, bytes) else response
   return response

def homeBasePost(auth_token, api, data=None):
   url = os.path.join(BASE_URL + api)
   # jsonheaderup={'Content-Type': 'multipart/form-data', 'Authorization': 'Token ' + auth_token}
   # response = requests.post(url, data=data, headers=jsonheaderup)
   response = TDIOUtils.http_post_multipart(auth_token, BASE_URL, api, data, None)
   response = response.decode('utf-8') if isinstance(response, bytes) else response
   return response

def homeBasePut(auth_token, api, data=None):
   url = os.path.join(BASE_URL + api)
   # jsonheaderup={'Content-Type': 'multipart/form-data', 'Authorization': 'Token ' + auth_token}
   # response = requests.put(url, data=data, headers=jsonheaderup)
   response = TDIOUtils.http_put_multipart(auth_token, BASE_URL, api, data, None)
   response = response.decode('utf-8') if isinstance(response, bytes) else response
   return response

def saveInferenceStatus(auth_token, taskid, status, state, reason, timestamp, progress):
   inferencestate = {'taskid':taskid, 'status':status, 'state':state, 'timestamp':timestamp, 'reason': reason, 'progress': progress}
   response = homeBaseGet(auth_token, '/task/inferencestatus', queryparams=inferencestate)

def open3dSlicer(pythonScript):
   slicerLaunchCommand = "{} --python-code \"{}\"".format(os.path.join(SLICER_DIR, SLICER_EXE), pythonScript)
   print('test', slicerLaunchCommand, flush=True)
   slicerCommandBase64 = base64.b64encode(bytearray(slicerLaunchCommand, 'unicode_escape'))
   slicerLaunchCommand = "echo  {} > {}".format(slicerCommandBase64.decode(), PIPE)
   import sys
   sys.stdout.flush()
   proc = subprocess.Popen([slicerLaunchCommand], stdout=subprocess.PIPE, shell=True)
   (out, err) = proc.communicate()
   # print(out)
   if proc.returncode != 0:
      raise Exception('Slicer did not work'.format(slicerLaunchCommand))
   else:
      print(out.decode('ascii'))

pythonScriptContent1 = "import slicer, vtk\nimport SimpleITK as sitk\nimport sitkUtils\ndef loadMasterAndSegmentationVolume(masterVolumeNiiPath, segmentationVolumeNiiPath):\n    masterVolumeNode = slicer.util.loadVolume(masterVolumeNiiPath)\n#    labelmapVolumeNode = slicer.util.loadLabelVolume(segmentationVolumeNiiPath)\n#    labelImage = sitk.ReadImage(segmentationVolumeNiiPath)\n#    labelmapVolumeNode = sitkUtils.PushVolumeToSlicer(labelImage, None, className='vtkMRMLLabelMapVolumeNode')\n#    segmentIDArray = vtk.vtkStringArray()\n#    segmentIDArray.SetNumberOfValues(1)\n#    segmentIDArray.SetValue(0, segmentID)\n    slicer.modules.SegmentEditorTDIOInstance.instance.self().loadMasterVolume(masterVolumeNiiPath)\n\nslicer.trainingdataiodata = {}\n\nloadMasterAndSegmentationVolume('{}', '{}')"

def open3dSlicerWithMasterSegmentationVolumes(trainingdataiodata, masterVolumeFilePath, segmentationVolumeFilePath):
   print('open3dSlicerWithMasterSegmentationVolumes:', masterVolumeFilePath)
   pythonScript = pythonScriptContent1.format(trainingdataiodata, masterVolumeFilePath, segmentationVolumeFilePath)
   open3dSlicer(pythonScript)
   print('open3dSlicerWithMasterSegmentationVolumes:--')

def convertDicomDirectoryToNifti(directorypath, niftifilepath):
   print('convertDicomDirectoryToNifti:', directorypath, niftifilepath)
   dicom2nifti.dicom_series_to_nifti(directorypath, niftifilepath, reorient_nifti=True)
   print(os.path.exists(niftifilepath))
   print('convertDicomDirectoryToNifti:--')

def hexa2rgba(hexstr, opacity):
    rgba = 'rgba({},{},{},{})'.format(int(hexstr[-6:-4], 16), int(hexstr[-4:-2], 16),int(hexstr[-2:], 16),opacity)
    return rgba

def createUrlToFetchFromS3(instanceUrl):
    newUrl = instanceUrl
    if ('s3.amazonaws' in instanceUrl):
        urlsplit = instanceUrl.split('trainingdataio/')
        if (len(urlsplit) > 1):
             # newUrl = createPresignedUrl('trainingdataio', urlsplit[1])
             if 'dicomweb' in instanceUrl:
                 newUrl = newUrl.replace("https", "dicomweb")
    return newUrl

def pngToNumpy(pngfilepath):
   splitext = os.path.splitext(pngfilepath)
   img = Image.open(pngfilepath).convert('L')

   img = img.transpose(Image.ROTATE_270)   # maybe not needed
   np_file = np.array(img)
   outputnumpyfilepath = pngfilepath.replace(splitext[1], '.npy')
   np.save(outputnumpyfilepath, np_file)
   return outputnumpyfilepath
                                               
'''
import slicer, vtk
import SimpleITK as sitk
import sitkUtils
def loadMasterAndSegmentationVolume(masterVolumeNiiPath, segmentationVolumeNiiPath):
     masterVolumeNode = slicer.util.loadVolume(masterVolumeNiiPath)
#     labelmapVolumeNode = slicer.util.loadLabelVolume(segmentationVolumeNiiPath)
#    labelImage = sitk.ReadImage(segmentationVolumeNiiPath)
#    labelmapVolumeNode = sitkUtils.PushVolumeToSlicer(labelImage, None, className='vtkMRMLLabelMapVolumeNode')
#     segmentIDArray = vtk.vtkStringArray()
#    segmentIDArray.SetNumberOfValues(1)
#    segmentIDArray.SetValue(0, segmentID)
#     slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, masterVolumeNode, segmentIDArray)
     slicer.modules.SegmentEditorTDIOInstance.instance.self().loadMasterVolume(masterVolumeNiiPath)
slicer.trainingdataiodata = {}
loadMasterAndSegmentationVolume('{}', '{}')
'''
