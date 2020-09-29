import os
import json

from pyunpack import Archive
import tarfile
import cv2
import numpy as np
import datetime
from collections import Counter
import codecs
from pycocotools import mask as mask_util
from pycocotools import coco as coco_loader
import requests
import string

# we need it to filter out non-ASCII characters otherwise
# trainning will crash
printable = set(string.printable)

def getAllClasses(labelingInterface):
    classes = {}
    if ('tools' in labelingInterface) and (len(labelingInterface['tools']) > 0):
        for classobj in labelingInterface['tools']:
            if 'attributes' in classobj:
              atts = classobj['attributes']
            else:
              atts = []
            classes[classobj['name']] = {'color':classobj['color'], 'attributes': atts}
    return classes

def hex_to_rgb(value):
    """Return (red, green, blue) for the color given as #rrggbb."""
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def hex_to_bgr(value):
    """Return (red, green, blue) for the color given as #rrggbb."""
    value = value.lstrip('#')
    lv = len(value)
    retval = tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return retval[::-1]

def rgb_to_hex(red, green, blue):
    """Return color as #rrggbb for the given color values."""
    return '#%02x%02x%02x' % (red, green, blue)

def getFileName(filepath):
    dirname = os.path.dirname(filepath)
    dirname = os.path.basename(dirname)
    filename, ext = os.path.splitext(os.path.basename(filepath))
    filename = unquote(filename)
    return (os.path.join(dirname, filename), ext)

def filterExportFiles(user, exportJsonString):
    if not user or user.is_anonymous:
       return ""
    exportoutput = {}
    if exportJsonString and len(exportJsonString) > 0:
        exportoutput = json.loads(exportJsonString)
    if not user.email in exportoutput:
        return ""
    retval = []
    for url in exportoutput[user.email]:
        if ('s3.amazonaws' in url):
           urlsplit = url.split('trainingdataio/')
           if (len(urlsplit) > 1):
               newUrl = createPresignedUrl('trainingdataio', urlsplit[1])
               retval.append(newUrl)
    return json.dumps(retval, ensure_ascii=False)

def exportMasks(job, projectjobjson, classes, output_dir, background_color, mask_bitness, mask_dirname='mask', exclude_dirname=False):
  output_dir = os.path.join(output_dir, mask_dirname)
  try:
    if not Path(output_dir).exists():
        Path(output_dir).mkdir()
    # read annotations
    imageCount = 0
    for series in projectjobjson['images']['seriesList']:
        for instance in series['instanceList']:
            imageCount += 1
            imageId =  instance['imageId'].split('?')[0]
            imageId = unquote(imageId)
            if exclude_dirname:
              filename = os.path.splitext(imageId)[0]
              filename = os.path.basename(filename)
            else:
              filename = getFileName(imageId)[0]
            maskfilepath = os.path.join(output_dir.strip(), filename)
            if not Path(os.path.dirname(maskfilepath)).exists():
               Path(os.path.dirname(maskfilepath)).mkdir()
            createMaskFile(job, instance, maskfilepath, classes, background_color, mask_bitness)
  except Exception as ex:
    print(str(ex))
  return output_dir

def getPointsFromRectangleRoi(rectangleroi):
    retvalpoints = []
    retvalpoints.append([rectangleroi['handles']['start']['x'], rectangleroi['handles']['start']['y']])
    retvalpoints.append([rectangleroi['handles']['end']['x'], rectangleroi['handles']['start']['y']])
    retvalpoints.append([rectangleroi['handles']['end']['x'], rectangleroi['handles']['end']['y']])
    retvalpoints.append([rectangleroi['handles']['start']['x'], rectangleroi['handles']['end']['y']])
    return retvalpoints

def getPointsFromPolygon(polygon):
    retvalpoints = []
    for handle in polygon['handles']:
        retvalpoints.append([handle['x'], handle['y']])
    return retvalpoints

def getPointFromSeedAnnotate(seedAnnotate):
    retval = {}
    p = seedAnnotate['handles']['end']
    retval['x'] = p['x']
    retval['y'] = p['y']
    return retval

def createMaskFile(jobid, instance, maskfilepath, classes, backgroundcolor, maskbitness):
    response = homeBaseGet(auth_token, '/cornerstoneannotation', queryparams={'job': jobid, 'instanceId':instance['instanceId']})
    cornerstoneAnnotations = []
    cornerstoneAnnotations = json.loads(response)
    print(instance['instanceId'], len(cornerstoneAnnotations))
    if len(cornerstoneAnnotations) == 0:
       return
    imageId = instance['imageId'].split('?')[0]
    imageId = unquote(imageId)
    mask = None
    for ca in cornerstoneAnnotations:
      jsonobj = json.loads(ca.jsonstring)
      annotations = jsonobj['annotations']
      if not isinstance(annotations, list) and len(annotations) > 0:
        annotations = annotations[next(iter(annotations))]
      # if len(annotations) == 0 or 'height' not in jsonobj or 'width' not in jsonobj:
      if len(annotations) == 0:
        print('error not exporting annotation:', instance, jsonobj)
        continue
      useremail = ca.annotator
      height = 2160 
      width = 3840
      if 'height' in jsonobj:
        height = int(jsonobj['height'])
      if 'width' in jsonobj:
        width = int(jsonobj['width'])
      mask = np.full((height, width, maskbitness // 8), backgroundcolor, dtype=np.uint8)
      for annotation in annotations:
          #print(annotation)
          toolData = annotation['toolData']
          toolType = annotation['toolName']
          color = annotation['selectedColor']
          if not toolData or len(toolData) == 0 or len(color) == 0 or not toolType or len(toolType) == 0:
            continue
          color = hex_to_bgr(annotation['selectedColor'])
          aclass = annotation['annotationClass']
          print('exportmask:', instance['instanceId'], aclass, toolType, annotation['id'])
          label = ''.join(filter(lambda x: x in printable, aclass))
          for data in toolData:
              if not data['color'] or len(data['color']) == 0:
                continue
              color = hex_to_bgr(data['color'])
              if toolType == 'rectangleRoi':
                  points = np.array(getPointsFromRectangleRoi(data))
                  mask = cv2.fillPoly(mask, np.int32([points]), color=color)
              elif toolType == 'polygon' or toolType == 'freehand':
                  points = np.array(getPointsFromPolygon(data), dtype=np.float)
                  print('points', points, len(points))
                  mask = cv2.fillPoly(mask, np.int32([points]), color=color)
              elif toolType == '2dgrowthtool':
                  counterx = -1
                  for x in data['data']:
                      counterx += 1
                      if not x or x == 'null' or x == None:
                         continue
                      for y in x:
                          mask = cv2.circle(mask, (int(counterx), int(y)), 1, color, -1)
              elif toolType == 'seedAnnotate':
                  print('seedAnnotate', data)
                  point = getPointFromSeedAnnotate(data)
                  mask = cv2.circle(mask, (int(point['x']), int(point['y'])), 1, color=color)
      maskfilepathnew = maskfilepath.strip() + '-' + useremail + '.png'
      cv2.imwrite(maskfilepathnew.strip(), mask)
      print(maskfilepathnew)

def pointsToCocoPoints(points):
    retval = []
    for p in points:
        retval.append(p[0])
        retval.append(p[1])
    return retval

def exportCoco(task, job, projectjobjson, classes, attributes, output_dir):
  output_dir = os.path.join(output_dir, 'coco')
  try:
    if not Path(output_dir).exists():
        Path(output_dir).mkdir()
    cocofilepath = os.path.join(output_dir.strip(), str(task.id)+'-'+str(task.name)+'.coco.json')
    resultannotation = {
        'licenses': [],
        'info': {},
        'categories': [],
        'images': [],
        'annotations': [],
        'attributes': []
    }
    # read annotations
    imageCount = 0
    with open(cocofilepath, 'w') as cocofile:
      for series in projectjobjson['images']['seriesList']:
        for instance in series['instanceList']:
            imageCount += 1
            imageId =  instance['imageId'].split('?')[0]
            imageId = unquote(imageId)
            createCocoImage(job, instance, cocofile, classes, attributes, resultannotation)
      json.dump(resultannotation, cocofile, indent=2)
  except Exception as ex:
    print(str(ex))
  return output_dir

def createCocoImage(job, instance, cocofile, classes, attributes, resultannotation):
  try:
    response = homeBaseGet(auth_token, '/cornerstoneannotation', queryparams={'job': jobid, 'instanceId':instance['instanceId']})
    cornerstoneAnnotations = []
    cornerstoneAnnotations = json.loads(response)
    if len(cornerstoneAnnotations) == 0:
       return
    imageId = instance['imageId'].split('?')[0]
    imageId = unquote(imageId)
    jsonobj = json.loads(cornerstoneAnnotations[0].jsonstring)
    annotations = jsonobj['annotations']
    if not isinstance(annotations, list) and len(annotations) > 0:
      annotations = annotations[next(iter(annotations))]
    # if len(annotations) == 0 or 'height' not in jsonobj or 'width' not in jsonobj:
    if len(annotations) == 0:
        print('error not exporting:', instance, jsonobj)
        return
    new_img = {}
    new_img['coco_url'] = ''
    new_img['date_captured'] = ''
    new_img['flickr_url'] = ''
    new_img['license'] = 0
    filename, ext = getFileName(imageId)
    new_img['id'] = filename + ext
    new_img['file_name'] = os.path.basename(imageId)
    new_img['height'] = 2160 
    new_img['width'] = 3840
    if 'height' in jsonobj:
      new_img['height'] = int(jsonobj['height'])
    if 'width' in jsonobj:
      new_img['width'] = int(jsonobj['width'])
    resultannotation['images'].append(new_img)

    for ca in cornerstoneAnnotations:
      jsonobj = json.loads(ca.jsonstring)
      annotations = jsonobj['annotations']
      if not isinstance(annotations, list) and len(annotations) > 0:
        annotations = annotations[next(iter(annotations))]
      #if len(annotations) == 0 or 'height' not in jsonobj or 'width' not in jsonobj:
      if len(annotations) == 0:
        print('error not exporting annotation:', instance, jsonobj)
        continue
      for annotation in annotations:
        #print(annotation)
        toolData = annotation['toolData']
        toolType = annotation['toolName']
        color = annotation['selectedColor']
        if not toolData or len(toolData) == 0 or len(color) == 0 or not toolType or len(toolType) == 0:
          continue
        color = hex_to_bgr(annotation['selectedColor'])
        aclass = annotation['annotationClass']
        aid = annotation['id']
        annotator = ca.annotator
        label = ''.join(filter(lambda x: x in printable, aclass))
        if 'attributes' in annotation:
           classattributes = annotation['attributes']
        else:
           classattributes = []
        for data in toolData:
            if not ('color' in data) or len(data['color']) == 0:
                print(color)
            else:
                color = hex_to_bgr(data['color'])
            if toolType == 'rectangleRoi':
                points = np.array(getPointsFromRectangleRoi(data))
                cocoinsertannotationdata(new_img, aid, aclass, pointsToCocoPoints(points), resultannotation, classattributes, classes, annotator)
            elif toolType == 'polygon' or toolType == 'freehand':
                points = np.array(getPointsFromPolygon(data), dtype=np.float)
                cocoinsertannotationdata(new_img, aid, aclass, pointsToCocoPoints(points), resultannotation, classattributes, classes, annotator)
            elif toolType == '2dgrowthtool':
                counterx = -1
                points = []
                for x in data['data']:
                    counterx += 1
                    if not x or x == 'null' or x == None:
                       continue
                    for y in x:
                        points.append(int(counterx))
                        points.append(int(y))
                cocoinsertannotationdata(new_img, aid, aclass, points, resultannotation, classattributes, classes, annotator)
            elif toolType == 'seedAnnotate':
                print('seedAnnotate', data)
                point = getPointFromSeedAnnotate(data)
                cocoinsertannotationdata(new_img, aid, aclass, point, resultannotation, classattributes, classes, annotator)

      imageAttributes = jsonobj['imageAttributes']
      if not imageAttributes or len(imageAttributes) == 0:
        return
      cocoinsertattributedata(new_img, imageAttributes, resultannotation['attributes'], classes, attributes)
  except Exception as ex:
    print(str(ex))

def cocoinsertannotationdata(image, annotationid, classid, points, resultannotation, classattributes, classes, annotator):
    new_anno = {}
    new_anno['category_id'] = classid
    new_anno['id'] = annotationid
    new_anno['image_id'] = image['id']
    new_anno['iscrowd'] = 0
    new_anno['segmentation'] = points
    new_anno['attributes'] = []
    new_anno['annotator'] = annotator
    if classid in classes:
        cocoinsertattributedata(image, classattributes, new_anno['attributes'], classes, classes[classid]['attributes'])
    # area, bbox = polygon_area_and_bbox(points, image['width'], image['height'])
    # new_anno['area'] = float(np.sum(area))
    # new_anno['bbox'] = bbox
    resultannotation['annotations'].append(new_anno)

def cocoinsertattributedata(image, imageAttributes, parentarray, classes, libraryattributes):
    for attribute in imageAttributes:
        attribute['image_id'] = image['id']
        if attribute['name']:
            id = attribute['name'].split('attr_')[1][0:36]
            if id in libraryattributes:
              print(id, libraryattributes)
              attribute['name'] = libraryattributes[id]
        parentarray.append(attribute)

def polygon_area_and_bbox(polygon, height, width):
    """Calculate area of object's polygon and bounding box around it
    Args:
        polygon: objects contour represented as 2D array
        height: height of object's region (use full image)
        width: width of object's region (use full image)
    """
    rle = mask_util.frPyObjects(polygon, height, width)
    area = mask_util.area(rle)
    bbox = mask_util.toBbox(rle)
    bbox = [min(bbox[:, 0]),
            min(bbox[:, 1]),
            max(bbox[:, 0] + bbox[:, 2]) - min(bbox[:, 0]),
            max(bbox[:, 1] + bbox[:, 3]) - min(bbox[:, 1])]
    return area, bbox

class taskTrainingStatus(object):
  def post(taskid) -> dict:
    try:
      inferencestate = {'status':request.GET['status'], 'state':request.GET['state'], 'timestamp':request.GET['timestamp'], 'reason': request.GET['reason']}
      #db_task = models.Task.objects.get(pk=int(request.GET['taskid']))
      #db_task.inferencestate = json.dumps(inferencestate)
      #db_task.save()
      return '{}'
    except Exception as ex:
      return "Error: {}".format(inferencestate), 400

  def get(taskid) -> dict:
    try:
      #taskid = int(request.GET['taskid'])
      #db_task = models.Task.objects.get(pk=taskid)
      inferencestate = {}
      #if db_task.inferencestate:
      #  inferencestate = json.loads(db_task.inferencestate)
      return inferencestate
    except Exception as ex:
      return "Error: {}".format(inferencestate), 400
        

