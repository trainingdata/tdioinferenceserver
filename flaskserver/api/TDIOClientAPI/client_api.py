# Copyright (c) 2019, NVIDIA CORPORATION. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of NVIDIA CORPORATION nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import cgi
import ssl

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

import json
import logging
import mimetypes
import os
import sys
import tempfile
import uuid
import time
# import SimpleITK
import numpy as np


class TDIOClientAPI:
    """
    The TDIOClient object is constructed with the server information

    :param api_version: TDIO Server API version
    """

    def __init__(self, api_version='v1'):
        self.api_version = api_version

        self.doc_id = None

    def getcornerstoneannotation (self, server_url, authtoken, jobid, seriesid, instanceid, annotatoremail):
        """
        Get the cornerstone annotation
        """
        url = '/cornerstoneannotation'
        query = '/' + '?job=' + TDIOUtils.urllib_quote_plus(jobid) + '&instanceId=' +  TDIOUtils.urllib_quote_plus(instanceid) + '&seriesId=' + TDIOUtils.urllib_quote_plus(seriesid) + '&annotator=' + TDIOUtils.urllib_quote_plus(annotatoremail)
        
        response = TDIOUtils.http_get_method(authtoken, server_url, url + query)
        response = response.decode('utf-8') if isinstance(response, bytes) else response
        retval = json.loads(response)
        return retval 

    def postcornerstoneannotation (self, server_url, authtoken, jobid, seriesid, instanceid, annotatoremail, data):
        """
        Get the cornerstone annotation
        """
        url = '/cornerstoneannotation'
        
        response = TDIOUtils.http_post_multipart(authtoken, server_url, url, data, None)
        response = response.decode('utf-8') if isinstance(response, bytes) else response
        return response

    def putcornerstoneannotation (self, server_url, id, authtoken, jobid, seriesid, instanceid, annotatoremail, data):
        """
        Get the cornerstone annotation
        """
        url = '/cornerstoneannotation/' + id
        
        response = TDIOUtils.http_put_multipart(authtoken, server_url, url, data, None)
        response = response.decode('utf-8') if isinstance(response, bytes) else response
        return response

    def convertImagePolygonsToCornerstoneannotations(self, imagepolygonslist, segmentationid, segmentationcolor): 
        print('segmentationcolor',segmentationcolor)
        tooldatas = []
        for polygon in imagepolygonslist:
            # print(polygon)
            tooldata = {"id": str(uuid.uuid4()),
                    "visible": True,
                    "active": False,
                    "alwaysActive": True,
                    "canComplete": False,
                    "invalidated": True,
                    "highlight": False,
                    "selectedClass": segmentationid,
                    "color": segmentationcolor,
                    "fillColor": TDIOUtils.hexa2rgba(segmentationcolor, 0.3),
                    "fillStyle": TDIOUtils.hexa2rgba(segmentationcolor, 0.3),
                    "textBox": {"active": False, "allowOutsideImage": True, "drawnIndependently": True, "hasBoundingBox": True, "hasMoved": False, "movesIndependently": False},
                    "handles": []}
            lastindex = -1
            for vertex in polygon:
                #print(vertex)
                if (lastindex >= 0):
                    tooldata["handles"][lastindex]["lines"].append({"x":vertex[1], "y":512-vertex[0]})
                tooldata["handles"].append({"x": vertex[1], "y":512-vertex[0], "highlight":True, "active":True, "lines":[]});
                lastindex = lastindex + 1
            tooldatas.append(tooldata)
        return tooldatas

    def convertToCornerstoneAnnotations(self, server_url, authtoken, seriesjson, listimagelistpolygons, segmentationid, segmentationcolor, jobid, useremail):
        # iterate over listimagelistpolygons
        instanceindex = -1
        listimagelistpolygons = list(reversed(listimagelistpolygons))
        for instance in seriesjson["instanceList"]:
            instanceindex = instanceindex + 1
            instanceid = instance["instanceId"]
            if len(listimagelistpolygons) < instanceindex+1:
                return
            imagepolygonslist = listimagelistpolygons[instanceindex]
            tooldatas = self.convertImagePolygonsToCornerstoneannotations(imagepolygonslist, segmentationid, segmentationcolor)
            print(instanceid, len(tooldatas))
            if len(tooldatas) == 0:
                continue
            newannotation = {
                        "id": str(uuid.uuid4()),
                        "annotationClass": segmentationid,
                        "annotationName": "",
                        "selectedColor": segmentationcolor,
                        "toolName": "freehand",
                        "toolData": tooldatas,
                        "toolDataIndex": 0,
                        "annotatedOn": int(time.time()),
                        "classAttributes": {},
                        "useremail": useremail
                    }
            response = self.getcornerstoneannotation(server_url, authtoken, jobid, seriesjson["seriesId"], instanceid, useremail)
            cannotations = []
            cannotations = response
            print(jobid, instanceid, seriesjson["seriesId"], cannotations)
            if len(cannotations) == 0 or not cannotations[0]["jsonstring"] or cannotations[0]["jsonstring"] == None or cannotations[0]["jsonstring"] == "":
                existingannotations = {"annotations": [], "stats":[], "imageAttributes":[], "lastmodified":int(time.time()), "labelCount":len(tooldatas), "reviews":[], "width":512, "height":512}
                cannotations.append({"job":jobid, "instanceId":instanceid, "seriesId":seriesjson["seriesId"]})
            else:
                existingannotations = json.loads(cannotations[0]["jsonstring"])

            existingannotations["annotations"].append(newannotation)
            cannotations[0]["jsonstring"] = json.dumps(existingannotations, ensure_ascii=False)
            cannotations[0]["annotator"] = useremail
            if "id" in cannotations[0]:
                pk = str(cannotations[0]["id"])
                del cannotations[0]["id"]
                response = self.putcornerstoneannotation(server_url, pk, authtoken, jobid, seriesjson["seriesId"], instanceid, useremail, json.dumps(cannotations[0]))
            else:
                response = self.postcornerstoneannotation(server_url, authtoken, jobid, seriesjson["seriesId"], instanceid, useremail, json.dumps(cannotations[0]))
            print(response)

import string
printable = set(string.printable)
class TDIOUtils:
    def __init__(self):
        pass

    @staticmethod
    def http_get_method(authtoken, server_url, selector):
        logger = logging.getLogger(__name__)
        logger.debug('Using Selector: {}{}'.format(server_url, selector))
        server_url = server_url.replace('localhost','parenthost').replace('127.0.0.1','parenthost')
        headers = {'Authorization': 'Token ' + authtoken}
        parsed = urlparse(server_url)
        if parsed.scheme == 'https':
            logger.debug('Using HTTPS mode')
            # noinspection PyProtectedMember
            conn = httplib.HTTPSConnection(parsed.hostname, parsed.port, context=ssl._create_unverified_context())
        else:
            conn = httplib.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
        try:
            conn.request('GET', selector, None, headers=headers)
            response = conn.getresponse()
        except Exception as ex:
            print(ex)
        return response.read()

    @staticmethod
    def http_post_multipart(authtoken, server_url, selector, fields, files, multipart_response=True):
        logger = logging.getLogger(__name__)
        logger.debug('Using Selector: {}{}'.format(server_url, selector))

        server_url = server_url.replace('localhost','parenthost').replace('127.0.0.1','parenthost')
        parsed = urlparse(server_url)
        if parsed.scheme == 'https':
            logger.debug('Using HTTPS mode')
            # noinspection PyProtectedMember
            conn = httplib.HTTPSConnection(parsed.hostname, parsed.port, context=ssl._create_unverified_context())
        else:
            conn = httplib.HTTPConnection(parsed.hostname, parsed.port)

        # content_type, body = TDIOUtils.encode_multipart_formdata(fields, files)
        body = fields.encode('utf-8')
        headers = {'Content-Type': 'application/json', 'content-length': str(len(body)), 'Authorization': 'Token ' + authtoken}
        # headers = {'content-type': content_type, 'content-length': str(len(body)), 'Authorization': 'Token ' + authtoken}
        conn.request('POST', selector, body, headers)

        response = conn.getresponse()
        logger.debug('Error Code: {}'.format(response.status))
        logger.debug('Error Message: {}'.format(response.reason))
        logger.debug('Headers: {}'.format(response.getheaders()))

        return response.read()
        if multipart_response:
            form, files = TDIOUtils.parse_multipart(response.fp if response.fp else response, response.msg)
            logger.debug('Response FORM: {}'.format(form))
            logger.debug('Response FILES: {}'.format(files.keys()))
            return form, files
        return response.read()

    @staticmethod
    def http_put_multipart(authtoken, server_url, selector, fields, files, multipart_response=True):
        logger = logging.getLogger(__name__)
        logger.debug('Using Selector: {}{}'.format(server_url, selector))

        server_url = server_url.replace('localhost','parenthost').replace('127.0.0.1','parenthost')
        parsed = urlparse(server_url)
        if parsed.scheme == 'https':
            logger.debug('Using HTTPS mode')
            # noinspection PyProtectedMember
            conn = httplib.HTTPSConnection(parsed.hostname, parsed.port, context=ssl._create_unverified_context())
        else:
            conn = httplib.HTTPConnection(parsed.hostname, parsed.port)

        # content_type, body = TDIOUtils.encode_multipart_formdata(fields, files)
        body = fields.encode('utf-8')
        headers = {'Content-Type': 'application/json', 'content-length': str(len(body)), 'Authorization': 'Token ' + authtoken}
        # headers = {'content-type': content_type, 'content-length': str(len(body)), 'Authorization': 'Token ' + authtoken}
        conn.request('PUT', selector, body, headers)

        response = conn.getresponse()
        logger.info('Error Code: {}'.format(response.status))
        logger.info('Error Message: {}'.format(response.reason))
        logger.info('Headers: {}'.format(response.getheaders()))

        return response.read()
        if multipart_response:
            form, files = TDIOUtils.parse_multipart(response.fp if response.fp else response, response.msg)
            logger.debug('Response FORM: {}'.format(form))
            logger.debug('Response FILES: {}'.format(files.keys()))
            return form, files
        return response.read()

    @staticmethod
    def save_result(files, result_file):
        logger = logging.getLogger(__name__)
        if len(files) > 0:
            for name in files:
                data = files[name]
                logger.debug('Saving {} to {}; Size: {}'.format(name, result_file, len(data)))

                dir_path = os.path.dirname(os.path.realpath(result_file))
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)

                with open(result_file, "wb") as f:
                    if isinstance(data, bytes):
                        f.write(data)
                    else:
                        f.write(data.encode('utf-8'))
                break

    @staticmethod
    def encode_multipart_formdata(fields, files):
        limit = '----------lImIt_of_THE_fIle_eW_$'
        lines = []
        for (key, value) in fields.items():
            lines.append('--' + limit)
            lines.append('Content-Disposition: form-data; name="%s"' % key)
            lines.append('')
            lines.append(value)
            print('encode_multipart_formdata', key, value)
        if files:    
            for (key, filename) in files.items():
                lines.append('--' + limit)
                lines.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
                lines.append('Content-Type: %s' % TDIOUtils.get_content_type(filename))
                lines.append('')
                with open(filename, mode='rb') as f:
                    data = f.read()
                    lines.append(data)
        lines.append('--' + limit + '--')
        lines.append('')

        body = bytearray()
        for l in lines:
            body.extend(l if isinstance(l, bytes) else l.encode('utf-8'))
            body.extend(b'\r\n')

        content_type = 'multipart/form-data; boundary=%s' % limit
        return content_type, body

    @staticmethod
    def get_content_type(filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    @staticmethod
    def parse_multipart(fp, headers):
        logger = logging.getLogger(__name__)
        print(fp, headers)
        fs = cgi.FieldStorage(
            fp=fp,
            environ={'REQUEST_METHOD': 'POST'},
            headers=headers,
            keep_blank_values=True
        )
        form = {}
        files = {}
        if hasattr(fs, 'list') and isinstance(fs.list, list):
            for f in fs.list:
                logger.debug('FILE-NAME: {}; NAME: {}; SIZE: {}'.format(f.filename, f.name, len(f.value)))
                if f.filename:
                    files[f.filename] = f.value
                else:
                    form[f.name] = f.value
        return form, files

    # noinspection PyUnresolvedReferences
    @staticmethod
    def urllib_quote_plus(s):
        return quote_plus(s)

    @staticmethod
    def hex_to_rgb(value):
        """Return (red, green, blue) for the color given as #rrggbb."""
        value = value.lstrip('#')
        lv = len(value)
        retval = [int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3)]
        retval[:] = [x / 255 for x in retval]
        return retval
        
    @staticmethod
    def rgb_to_hex(rgb):
        """Return (red, green, blue) for the color given as #rrggbb."""
        value = '#%02x%02x%02x' % (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
        return value

    @staticmethod
    def hexa2rgba(hexstr, opacity):
        rgba = 'rgba({},{},{},{})'.format(int(hexstr[-6:-4], 16), int(hexstr[-4:-2], 16),int(hexstr[-2:], 16),opacity)
        return rgba
