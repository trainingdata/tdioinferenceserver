import inspect
import pydicom
import numpy as np
#import png
from PIL import Image
import json
import os

def pydicom_as_dict(ds):
    data = {}
    for key in ds.dir():
        attribute = ds.get(key)
        data[key] = pydicom_to_native_type(attribute)
    return data


native_types = [
    str,
    int,
    float,
    list,
    dict,
    bytes
]

lists = [
    pydicom.sequence.Sequence,
    pydicom.multival.MultiValue
]

floats = [
    pydicom.valuerep.DSdecimal,
    pydicom.valuerep.DSfloat
]

def pydicom_to_native_type(value):
    value_type = type(value)

    if value_type in native_types:
        return value

    if value_type is pydicom.valuerep.IS:
        return int(str(value))

    if value_type in floats:
        return float(str(value))

    if value_type in lists:
        new_list = []
        for new_value in value:
            new_list.append(pydicom_to_native_type(new_value))
        return new_list

    if value_type is pydicom.dataset.Dataset:
        new_object = {}
        for test_key in value.keys():
            if type(test_key) is pydicom.tag.BaseTag:
                new_key = str(test_key)
            else:
                new_key = test_key

            new_key = str(test_key)
            new_object[new_key] = pydicom_to_native_type(value[test_key])
        return new_object

    # Extract just the value, as the "tag" should be the key anyways.
    if value_type is pydicom.dataelem.DataElement:
        return value.value

    return str(value)

def dicom_to_npy_data(dicom_filename):
  try:
    ds = pydicom.dcmread(dicom_filename, force=True)
    shape = ds.pixel_array.shape

    #Convert to float to avoid overflow or underflow losses.
    image_2d = ds.pixel_array

  except Exception as ex:
    print(str(ex))
    return None

  return image_2d
    
def pydicom_to_npy(dicom_filename, outputwidth, outputheight):
  try:
    filepart = os.path.splitext(dicom_filename)
    numpy_filename = filepart[0] + '.npy'
    print(numpy_filename)

    image_2d = dicom_to_npy_data(dicom_filename)

    # Rescaling grey scale between 0-255
    image_2d_scaled = (np.maximum(image_2d,0) / image_2d.max()) * 255.0

    #Convert to uint
    image_2d_scaled = np.uint8(image_2d_scaled)

    # crop center
    if image_2d_scaled.shape[1] > outputwidth or image_2d_scaled.shape[0] > outputheight:
      image_2d_scaled = crop_center(image_2d_scaled, outputwidth, outputheight)

    # Write numpy file
    print('shape' + str(image_2d_scaled.shape))
    np.save(numpy_filename, image_2d_scaled)
  except Exception as ex:
    print(str(ex))
    return None
  return numpy_filename

#maskvalues = {0:0, 31:1, 83:2, 111:3, 174:4, 191:5, 226:6}  # color value. you find it by printing out unique values of the mask numpy array

def png_to_npy(from_file_path, to_path_mask, outputfilewidth, outputfileheight, maskvalues):
  print('maskvalues', maskvalues)
  try:
    img = Image.open(from_file_path).convert('RGB').convert('L')
    #img = img.transpose(Image.ROTATE_270)   # maybe not needed
    np_file = np.array(img)
    print(np.unique(np_file))
    for i in range(len(np_file)):
     for j in range(len(np_file[i])):
      if np_file[i][j] in maskvalues:
        np_file[i][j] = maskvalues[np_file[i][j]] 
      else:
        np_file[i][j] = 0
 
    print('mask shape' + str(np_file.shape))
    if np_file.shape[1] > outputfilewidth or np_file.shape[0] > outputfileheight:
      np_file = crop_center(np_file, outputfilewidth, outputfileheight)
    np.save(to_path_mask, np_file)
  except Exception as ex:
    print(str(ex))
    raise ex
    
def scale_npy_image(input_image, new_width):
    retval = input_image.thumbnail(new_width, Image.ANTIALIAS)
    return retval

def crop_center(img,cropx,cropy):
    y,x = img.shape
    startx = x//2-(cropx//2)
    starty = y//2-(cropy//2)    
    return img[starty:starty+cropy,startx:startx+cropx]

def generateBlackNumpyLabel(filepath, outputfilewidth, outputfileheight):
  try:
    np_data = np.ndarray((outputfileheight, outputfilewidth), dtype=np.uint8)
    np.save(filepath, np_data)
  except Exception as ex:
    raise ex

# if __name__ == "__main__":
#     import sys, os
#     from shutil import copyfile
#     argv = sys.argv
#     jsonoutput = [] 
#     in_dir_path = argv[1]
#     copy_file = 'label-0-320x320.npy'
#     for root, subdirs, files in os.walk(in_dir_path):
#         #print(root)
#         print('Processing:', subdirs)
#         #print(files)
#         for file in files:
#             if file.endswith(".dcm"):
#                 dicom_filename = os.path.join(root, file)
#                 npy_filename = os.path.join(root, file.replace('.dcm', '.npy'))
#                 pydicom_to_npy(dicom_filename, npy_filename)
#             if file.endswith('.png'):
#                 print('Processing:', file)
#                 png_filename = os.path.join(root, file)
#                 npy_filename = os.path.join(root, file.replace('.png', '.npy'))
#                 png_to_npy(png_filename, npy_filename)
#         for file in files:
#             if file.endswith(".dcm"):
#                 dicom_filename = os.path.join(root, file)
#                 dicom_data = pydicom.dcmread(dicom_filename)
#                 npy_filename = os.path.join(root, file.replace('.dcm', '.npy'))
#                 jobj = {'image': npy_filename, 'label': npy_filename.replace('.npy', '-micelys.quintana.ai@gmail.com.npy')}
#                 jsonoutput.append(jobj)
#                 img = np.load(jobj['image'])
#                 if img.shape[0] == 384:
#                     new_img = crop_center(img, 320, 320)
#                     np.save(jobj['image'], new_img)
#                     print('######### cropped dcmnpy', new_img.shape)
#                 if not os.path.exists(jobj['label']):
#                     print('################ missing label:', jobj['label'], 'copy file:', copy_file)
#                     copyfile(copy_file, jobj['label'])
#                 else:
#                     label = np.load(jobj['label'])
#                     w = label.shape[0]
#                     print(w, w)
#                     if w == 384:
#                         new_label = crop_center(label, 320, 320)
#                         np.save(jobj['label'], new_label)
#                         print('######### cropped labelnpy', new_label.shape)
#     print('#######################################################################################')
#     print(json.dumps(jsonoutput))
