import os
from .utils import pngToNumpy, convertDicomDirectoryToNifti
from .dicom import pydicom_to_npy
import nibabel as nib
import cv2
import uuid
import subprocess
import json
import numpy as np

def sortedContours(contours):
    sortedcontours = []
    for c_i in range(len(contours)):
        c_tmp = contours[c_i]
        c_tmp_sorted = np.reshape(c_tmp, [c_tmp.shape[0], c_tmp.shape[2]])
        c_tmp_sorted = c_tmp_sorted.tolist()
        if len(c_tmp_sorted) > 5:
            c_tmp_sorted = [c_tmp_sorted[p_idx] for p_idx in range(0, len(c_tmp_sorted), 1 + 1)]
        sortedcontours.append(c_tmp_sorted)
    return sortedcontours

def niftiMaskToContours2D(outputfilepath):
    i5 = nib.load(outputfilepath)
    numpydata5 = i5.get_fdata().astype(np.uint8)
    width = numpydata5.shape[1]
    height = numpydata5.shape[0]
    contours, hierarchy = cv2.findContours(numpydata5, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return width, height, sortedContours(contours)

def niftiMaskToContours3D(outputfilepath):
    i5 = nib.load(outputfilepath)
    volumemask = i5.get_fdata().astype(np.uint8)
    width = volumemask.shape[1]
    height = volumemask.shape[0]
    slicecount = volumemask.shape[2]
    contours3d = []
    for sliceidx in range(slicecount):
        contours_tmp, h = cv2.findContours(volumemask[:, :, sliceidx], cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours3d.apend(sortedContours(contours_tmp))
    return width, height, contours3d
        
def inferenceOnNumpy2D(imagefilepath, instanceid, aiserver, mlmodelid, mlmodelinputwidth, mlmodelinputheight):
    returnjsonobj = []
    contours = []
    numpyfilepath = ''
    if imagefilepath.lower().endswith(".png") or imagefilepath.lower().endswith('.jpg') or imagefilepath.lower().endswith('.jpeg'): 
        numpyfilepath = pngToNumpy(imagefilepath)
    elif imagefilepath.lower().endswith(".dcm") or imagefilepath.lower().endswith(".dicom"):
        numpyfilepath = pydicom_to_npy(imagefilepath, mlmodelinputwidth, mlmodelinputheight)
    else:
        print('Error: no files (jpeg, png, dcm, dicom, nifti) for inferencing') 
        return returnjsonobj
    if not numpyfilepath:
        print('Error: no files (jpeg, png, dcm, dicom, nifti) for inferencing') 
        return returnjsonobj
        
    splitext = os.path.splitext(imagefilepath)
    outputfilepath = splitext[0] + '-result.nii.gz'
    # returnjsonobj.append(commonInferenceOnFile(numpyfilepath, outputfilepath, aiserver, mlmodel))
    print(numpyfilepath, outputfilepath)
    commonInferenceOnFile(numpyfilepath, outputfilepath, aiserver, mlmodelid)
    returnjsonobj.append(outputfilepath)
    # generate contours
    # width, height, contours = niftiMaskToContours2D(outputfilepath)
        
    return returnjsonobj

def inferenceOnNumpy3D(imagefiledir, instanceid, aiserver, aimodel):
    returnjsonobj = []
    twoDNiftiFiles = []
    for root, subdirs, files in os.walk(imagefiledir):
        for file in files:
            filepath = os.path.join(root, file)
            if filepath.lower().endswith(".png") or filepath.lower().endswith('.jpg') or filepath.lower().endswith('.jpeg'):
                numpyfilepath = pngToNumpy(filepath)
                splitext = os.path.splitext(filepath)
                outputfilepath = splitext[0] + '-result.nii.gz'
                # returnjsonobj.append(commonInferenceOnFile(numpyfilepath, outputfilepath, aiserver, aimodel))
                commonInferenceOnFile(numpyfilepath, outputfilepath, aiserver, aimodel)
                returnjsonobj.append(niioutputfilepath)

                # get contours
                # width, height, contours = niftiMaskToContours2D(outputfilepath)
                # returnjsonobj.append(contours)
                
    return returnjsonobj
            
def inferenceOnNiftiVolume(directorypath, seriesjson, aiserver, aimodel):    
    returnjsonobj = []
    # convert directorypath to
    r = str(uuid.uuid4())
    os.makedirs(os.path.join('/tmp', r))
    niifilepath = os.path.join('/tmp', r, r + '.nii.gz')
    niioutputfilepath = os.path.join('/tmp', r, r + '-result.nii.gz')
    print(directorypath, niifilepath)
    convertDicomDirectoryToNifti(directorypath, niifilepath)

    # TODO check file exists

    # do inference
    commonInferenceOnFile(niifilepath, niioutputfilepath, aiserver, aimodel)
    returnjsonobj.append(niioutputfilepath)
    return niioutputfilepath
    # do mask2Polygon
    # width, height, returnjsonobj = niftiMaskToContours3D(niioutputfilepath)
    #returnjsonobj = commonMask2Polygon(niioutputfilepath, aiserver)
    # returnjsonobj.append(niifilepath)
    # returnjsonobj.append(niioutputfilepath)
    # return width, height, returnjsonobj

def commonInferenceOnFile(inputfilepath, outputfilepath, aiserver, aimodel):
    # upload nifti file to aiserver
    url = os.path.join(aiserver, 'v1/segmentation?model=' + aimodel + '&output=image')
    curlcommand = 'curl -X POST \'' + url + '\' -H \'cache-control: no-cache\'   -H \'content-type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW\'  -F \'params={}\'   -F datapoint=@' + inputfilepath + ' > ' + outputfilepath
    print(curlcommand)
    result = os.system(curlcommand)

def commonMask2Polygon(inputfilepath, aiserver):
    jsonobj = []
    url = os.path.join(aiserver, 'v1/mask2polygon')
    curlcommand2 = 'curl -X POST \'' + url + '\' -H \'accept: application/json\' -H \'Content-Type: multipart/form-data\' -F \'params={ "more_points": 1 }\' -F \'datapoint=@' + inputfilepath + ';type=application/gzip\''
    print('curlcommand2', curlcommand2)
    proc = subprocess.Popen([curlcommand2], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    print('out', out) 
    if proc.returncode != 0:
        raise Exception('Curl {} did not work'.format(url))
    else:
        jsonobj = json.loads(out.decode('ascii')) 

    return jsonobj

