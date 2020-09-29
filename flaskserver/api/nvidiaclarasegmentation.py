import uuid
#from flask_injector import inject
#from services.elasticsearch import ElasticSearchIndex

import dicom2nifti
import os
import random
import uuid
import requests
#xfrom requests_toolbelt.multipart.encoder import MultipartEncoder
import subprocess
import json
from .utils import convertDicomDirectoryToNifti, pngToNumpy
import nibabel as nib
from .nvidiaclaraannotation import inferenceOnNumpy3D, inferenceOnNiftiVolume

def post(segmentationformdata) -> dict:
    directorypath = segmentationformdata['directorypath'][0]
    seriesjson = segmentationformdata['seriesjson'][0]
    aiserver = segmentationformdata['aiserver'][0]
    aimodel = segmentationformdata['aimodel'][0]
    print(directorypath, seriesjson, aiserver, aimodel)

    hasdcmniftifile = True
    for root, subdirs, files in os.walk(directorypath):
        for file in files:
            file = file.lower()
            if file.endswith(".png") or file.endswith('.jpg') or file.endswith('.jpeg'): 
                hasdcmniftifiles = False
            elif file.endswith(".dcm") or file.endswith('.nii.gz') or file.endswith('.nii'):
                hasdcmniftifile = True
    splitext = os.path.splitext(directorypath)
    print(hasdcmniftifile)
    if not hasdcmniftifile:
        numpyfilepath = directorypath.replace('png', 'npy')
        return inferenceOnNumpy3D(directorypath, numpyfilepath, aiserver, aimodel)
    else:
        return inferenceOnNiftiVolume(directorypath, seriesjson, aiserver, aimodel)

## saved for later use ##
#jsonheaderup={'accept': 'multipart/form-data','Content-Type': 'multipart/form-data'}
#with open(niifilepath, 'rb') as file:
#   print(url)
#   files = {('datapoint', ((os.path.basename(niifilepath), file, 'type=application/gzip'))), ('params', (None, '{}'))}
#   req = requests.Request('POST', url, files=files, headers=jsonheaderup)
# print(req.prepare().body)
#   response = requests.post(url, data=files, headers=jsonheaderup)
#   print(response)
#   with open(niioutputfilepath, 'wb') as outputfile:
#       outputfile.write(response.content)
#curl -X POST "http://35.199.170.121:5000/v1/segmentation?model=segmentation_liver&output=image" -H "accept: multipart/form-data" -H "Content-Type: multipart/form-data" -F "params={}" -F "datapoint=@randomnumber.nii.gz;type=application/gzip"
