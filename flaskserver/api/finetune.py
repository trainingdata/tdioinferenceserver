import os
import requests
import subprocess
import json
from .media_extractors import get_mime
from pyunpack import Archive
import time

processstdout = {}

def parseProgress(pid, stdoutfile):
  try:
    command = ['ps', str(pid)]
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=False)
    output,err = p.communicate()
    if str(pid) in output.decode('utf-8'):
      # running
      return 50
  except Exception as ex:
    print(str(ex))
  # not running anymore  
  return 100

class finetune(object):
  def post(args, archivefile) -> dict:
    try:
     global processstdout
     mlmodel = args['mlmodel'][0]
     modelversion = args['modelversion'][0]
     # get the new training data files & masks
     status = ''
     temp_dir = '/tmp'
     home_dir = os.environ.get('HOME')
     workspace_dir = os.path.join(home_dir, 'workspace', 'trainingdataio')
     # TODO clear samples dir path

     if not mlmodel or mlmodel == '':
        # fail
        status = "Failed: missing mlmodel"        
        print('failed:', status)
        return str(status), 400
    
     mlmodelid = mlmodel
     f = archivefile
     totalsize = 0
     totalsize += f.content_length
     mime = get_mime(f.filename)
     if mime == 'archive':
         path = os.path.join(temp_dir, f.filename)
         f.save(path)
         #with open(path, 'wb') as archivefile:
         #    for chunk in f.chunks():
         #        archivefile.write(chunk)
         Archive(path).extractall(workspace_dir)

         # now execute the API for fine-tune
         # url = 'http://127.0.0.1:5000/admin/fine_tune/' + mlmodelid
         # response = requests.post(url)
         # if response.status_code != 200:
         #    status = "failed {}".format(response.reason)
         shellcommand = 'docker ps -aqf \'name=nvidiaclara\''
         proc = subprocess.Popen([shellcommand], stdout=subprocess.PIPE, shell=True)
         (out, err) = proc.communicate()
         if proc.returncode != 0:
             raise Exception('{} did not work {}'.format(shellcommand, err))
         else:
             containerid = out.decode("utf-8").strip() 
             shellcommand = 'docker exec -d {} /bin/bash -c "cd /var/nvidia/aiaa/mmars/{} && export MMARS_ROOT=/var/nvidia/aiaa/mmars/{} && ./commands/train_finetune.sh"'.format(containerid, mlmodel, mlmodel)
             #['docker exec', '-it', containerid, '/bin/bash', ' -c \"cd /var/nvidia/aiaa/mmars/knee && export MMARS_ROOT=/var/nvidia/aiaa/mmars/knee && ./commands/train_finetune.sh\"']
             proc = subprocess.Popen(shellcommand, stdout=subprocess.PIPE, shell=True)
             (out, err) = proc.communicate()
             if proc.returncode != 0:
                 raise Exception('{} did not work {}'.format(shellcommand, err))
             else:
                 status = str(proc.pid)
                 processstdout[proc.pid] = proc.stdout
                 print('Sucess: {} {}'.format(status, shellcommand))
    except Exception as ex:
        status = "error exception: " + str(ex)
        print('failed:', status)
        return str(status), 400

    return status, 200    

  def get(finetuneid) -> dict:
    try:
        global processstdout
        finetuneid = int(finetuneid)
        print(finetuneid)
        retval = {"status": "", "progress": 0 , "timestamp": 0, "reason": "", "state": ""}
        if not finetuneid in processstdout:
          return json.dumps(retval), 404
        else:
          progress = parseProgress(finetuneid, processstdout[finetuneid])
          if progress == 100:
            retval['state'] = 'finished'
            retval['status'] = 'finished'
            retval['progress'] = 100 
          else:
            retval['state'] = 'running'
            retval['status'] = 'running'
            retval['progress'] = 56
            
          retval['timestamp'] = time.time()
          print('GET /finetune', retval)
          return json.dumps(retval), 200
    except Exception as ex:
      status = "error exception: " + str(ex)        
      return str(status), 400
