import requests
from multiprocessing import Pool
from urllib.request import urlretrieve
import os
import logging
global_logger = logging.getLogger(__name__)

def fetch_url(url, targetfile):
    global_logger.error(targetfile + url)  
    try:  
      if not os.path.exists(targetfile):
        if 'dicomweb' in url:
           url = url.replace('dicomweb', 'http')
        r = requests.get(url, stream=True)
        global_logger.error('status code {}'.format(r.status_code))
        if r.status_code == 200:
            with open(targetfile, 'wb') as f:
                global_logger.error(targetfile)
                for chunk in r:
                    f.write(chunk)
    except Exception as ex:
      global_logger.error(str(ex))
      raise ex
    return targetfile
    
def downloadResourceFolder(urls, targetfilepaths):
    #results = Pool(5).map(fetch_url, urls, targetfilepaths)
    #for r in results:
    #    print(r)
    #print(urls)
    #results = ThreadPool(5).map(urlretrieve, urls)
    result = []
    for a,b in zip(urls, targetfilepaths):
        result.append(fetch_url(a, b))
    return result
    
