import json
import requests
from threading import Timer
from . import utils
import time
import uuid
from .utils import homeBaseGet

def convert_points_to_rectangle(points, tool) :
    toolData = {}
    toolData['id'] = str(uuid.uuid4())
    toolData['visible'] = True
    toolData['active'] = True
    toolData['alwaysActive'] = False
    toolData['invalidated'] = True
    toolData['fillStyle'] = utils.hexa2rgba(tool['color'], 0.3)
    toolData['fillColor'] = utils.hexa2rgba(tool['color'], 0.3)
    toolData['color'] = utils.hexa2rgba(tool['color'], 0.3)
    toolData['selectedClass'] = tool['name']
    toolData['classSelected'] = tool['name']
    toolData['handles'] = {}
    toolData['handles']['textBox'] = {'active': False, 'allowOutsideImage': True, 'drawnIndependently': True, 'hasBoundingBox': True, 'hasMoved': False, 'movesIndependently': False}
    x_points = points[::2]
    y_points = points[1::2]
    toolData['handles']['start'] = {}
    toolData['handles']['end'] = {}
    toolData['handles']['start']['x'] = x_points[0]
    toolData['handles']['start']['y'] = y_points[0]
    toolData['handles']['end']['x'] = x_points[1]
    toolData['handles']['end']['y'] = y_points[1]
    return toolData

def convert_points_to_polygon(points, tool) :
    toolData = {}
    toolData['id'] = str(uuid.uuid4())
    toolData['visible'] = True
    toolData['active'] = False
    toolData['canComplete'] = False
    toolData['invalidated'] = True
    toolData['highlight'] = False
    toolData['fillStyle'] = utils.hexa2rgba(tool['color'], 0.3)
    toolData['color'] = utils.hexa2rgba(tool['color'], 0.3)
    toolData['selectedClass'] = tool['name']
    toolData['classSelected'] = tool['name']
    toolData['handles'] = []
    toolData['textBox'] = {'active': False, 'allowOutsideImage': True, 'drawnIndependently': True, 'hasBoundingBox': True, 'hasMoved': False, 'movesIndependently': False}
    x_points = points[::2]
    y_points = points[1::2]
    if len(x_points) == 2 :
        x_points.append(x_points[1])
        x_points.append(x_points[0])
        y_points.insert(0, y_points[0])
        y_points.append(y_points[2])

    index = 0
    for point in x_points:
        handle = {}
        handle['x'] = point
        handle['y'] = y_points[index]
        handle['lines'] = []
        index += 1

        if index < len(x_points) :
            nextHandle = {}
            nextHandle['x'] = x_points[index]
            nextHandle['y'] = y_points[index]
            nextHandle['highlight'] = True
            nextHandle['active'] = True
            handle['lines'].append(nextHandle)
        else :
            nextHandle = {}
            nextHandle['x'] = x_points[0]
            nextHandle['y'] = y_points[0]
            handle['lines'].append(nextHandle)

        toolData['handles'].append(handle)
    return toolData

def convert_points(tool, points) :
    toolData = {}
    if tool["tool"] == 'polygon':
        toolData = convert_points_to_polygon(points, tool)
    elif tool["tool"] == 'rectangle' :
        toolData = convert_points_to_rectangle(points, tool)
    return toolData

def create_cvat_annotations(item, tool) :
    annotation = {}
    annotation["id"] = str(uuid.uuid4())
    annotation["annotationClass"] = tool["name"]
    annotation["annotationName"] = ""
    annotation["selectedColor"] = tool["color"]
    annotation["toolName"] = tool["tool"]
    annotation["toolData"] = []
    annotation["toolDataIndex"] = "0"
    annotation["annotatedOn"] = time.time()
    annotation["classAttributes"] = []
    annotation["useremail"] = "auto@trainingdata.io"
    return annotation

def save_to_database(job, seriesId, instanceId, annotations, auth_token):
    annotator = 'auto@trainingdata.io'
    jsonstring = {}
    jsonstring["annotations"] = annotations
    jsonstring["stats"] = []
    jsonstring = json.dumps(jsonstring)
    url = "/cornerstoneannotation/?job="+str(job)+"&seriesId="+seriesId+"&instanceId="+instanceId+"&annotator=auto@trainingdata.io"
    annotations = json.loads(homeBaseGet(auth_token, url))
    if len(annotations) == 0 :
        data = {}
        data["job"] = job
        data["seriesId"] = seriesId
        data["instanceId"] = instanceId
        data["jsonstring"] = jsonstring
        data["annotator"] = annotator
        response = utils.homeBasePost(auth_token, '/cornerstoneannotation', json.dumps(data, ensure_ascii=False))
    else :
        data = annotations[0]
        data["jsonstring"] = jsonstring
        response = utils.homeBasePut(auth_token, '/cornerstoneannotation/'+ str(data["id"]), json.dumps(data, ensure_ascii=False))

def save_data(data, task, job, images, labelling_interface, mlmodel, auth_token):
    data = json.loads(data)
    data = data["shapes"]

    tools = labelling_interface["jsonstring"]["tools"]
    labelMapping = {}
    for tool in tools:
        labelMapping[tool["name"].lower()] = tool

    ann = {}
    for item in data:
        if item['label_id'] not in labelMapping:
            continue
        if item['frame'] not in ann :
            ann[item['frame']] = {}
        annotations = ann[item['frame']]
        if labelMapping[item['label_id']]["name"] not in annotations :
            annotations[labelMapping[item['label_id']]["name"]] = create_cvat_annotations(item, labelMapping[item['label_id']])
        annotation = annotations[labelMapping[item['label_id']]["name"]]
        annotation["toolData"].append(convert_points(labelMapping[item['label_id']], item["points"]))

    result = {}
    for key in ann:
        annotations = ann[key]
        result[key] = []
        for k in annotations:
            result[key].append(annotations[k])
        save_to_database(job, images[int(key)]["seriesId"], images[int(key)]["instanceId"], result[key], auth_token)

def check_inference_status(task, job, images, labelling_interface, mlmodel, url, auth_token, count=0):
    count += 1
    result = requests.get(url)
    result = json.loads(result.content.decode("utf-8"))

    progress = 'NA'
    if 'progress' in result :
        progress = result['progress']
    utils.saveInferenceStatus(auth_token, task["id"], result["status"], result["status"], '', int(time.time()), progress)

    if result["status"] != 'finished' and result["status"] != 'unknown':
        if count < 1800 :
            Timer(2, check_inference_status, [task, job, images, labelling_interface, mlmodel, url, auth_token, count]).start()
    elif result["status"] == 'finished':
        save_data(result["data"], task, job, images, labelling_interface, mlmodel, auth_token)

def validate_labelling_interface(task, labelling_interface, mlmodel, outputTool, auth_token):
    jsonstring = mlmodel["jsonconfig"]
    modellabels = jsonstring["labels"]

    index = 0
    for labels in modellabels:
        modellabels[index] = labels.strip()
        index += 1

    jsonstring = labelling_interface["jsonstring"]
    tools = jsonstring["tools"]
    replicate = False
    for tool in tools:
        if (tool["name"] in modellabels or tool["name"].lower() in modellabels) and tool["tool"] != outputTool:
            replicate = True
            tool["tool"] = outputTool

    jsonstring["tools"] = tools

    if replicate is True :
        print(jsonstring)
        print(labelling_interface)
        labelling_interface["jsonstring"] = json.dumps(jsonstring)
        labelling_interface.pop("id", None)
        labelling_interface["name"] = labelling_interface["name"] + " (Auto Generated)"
        # if 'description' not in labelling_interface :
        labelling_interface["description"] = "NA"
        print(labelling_interface)
        response = utils.homeBasePost(auth_token, '/labelinterfacetemplates', json.dumps(labelling_interface, ensure_ascii=False))
        print(response)

    return labelling_interface

def start_inferencing(task, job, mlmodel, labelling_interface, dataset, auth_token):
    if mlmodel["modeltype"] == 'tensorflow-objectsegmentation-maskrcnn' :
        baseurl = mlmodel["serverurl"] + '/tensorflow/segmentation'
        outputTool = 'polygon'
    elif mlmodel["modeltype"] == 'tensorflow-objectdetection-rcnn' :
        baseurl = mlmodel["serverurl"] + '/tensorflow/annotation'
        outputTool = 'polygon'
    else :
        return

    url = baseurl + '/create1/task/' + str(task["id"])
    checkurl = baseurl + '/check1/task/' + str(task["id"])

    # labelling_interface = validate_labelling_interface(task, labelling_interface, mlmodel, outputTool, auth_token)
    images = dataset

    print("Starting inference")
    image_list = []
    images = images["seriesList"]
    for series in images :
        instances = series['instanceList']
        for instance in instances :
            if 'dicomweb' in instance['imageId']:
                continue

            temp = {}
            temp['seriesId'] = series['seriesId']
            temp['instanceId'] = instance['instanceId']
            temp['imageId'] = instance['imageId'].replace('localhost','parenthost').replace('127.0.0.1','parenthost')
            # temp['imageId'] = utils.createUrlToFetchFromS3(instance['imageId'])
            image_list.append(temp)
    print(labelling_interface)
    labint = labelling_interface["jsonstring"]["tools"]
    labels = []

    for tool in labint:
        labels.append(tool["name"].lower())
    data = {}
    data['labels'] = labels
    data['dataset'] = image_list

    utils.saveInferenceStatus(auth_token, task["id"], 'queued', 'queued', '', int(time.time()), '0.0')
    temp = {}
    temp['data'] = data

    # result = requests.post(url, data=json.dumps(temp))

    Timer(2, check_inference_status, [task, job, image_list, labelling_interface, mlmodel, checkurl, auth_token, 0]).start()
    return

def start_autoannotation(task, mlmodel, projectjobjson, jobid, labelling_interface, auth_token) :
    dataset = projectjobjson['images']
    start_inferencing(task, jobid, mlmodel, labelling_interface, dataset, auth_token)
