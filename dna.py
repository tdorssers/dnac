"""
This module implements a northbound API client manager for DNA Center

Basic Usage:

  dnac = dna.Dnac('https://10.0.0.1/')
  dnac.login('admin', 'password')
  print(dnac.get('network-device/count'))
  dnac.close()

Or as a context manager:

  with dna.Dnac('https://10.0.0.1/') as dnac:
      dnac.login('admin', 'password')
      print(dnac.get('network-device/count'))
"""

# Author: Tim Dorssers

import json
import time
import logging
import requests
from requests import HTTPError

requests.packages.urllib3.disable_warnings()  # Disable warnings

class Dnac(requests.Session):
    """ Implements a REST API session manager for DNA Center """

    def __init__(self, url):
        super(Dnac, self).__init__()
        self.base_url = 'https://' + url.rsplit('://')[-1].split('/')[0]
        self.headers.update({'Content-Type': 'application/json'})
        self.verify = False  # Ignore verifying the SSL certificate

    def login(self, usr, passwd):
        """ Opens session to DNA Center """
        # Request token using HTTP basic authorization
        response = self.post('auth/token', ver='system/v1', auth=(usr, passwd))
        # Persist authorization token for further REST requests
        self.headers.update({'X-Auth-Token': response['Token']})

    def request(self, method, api, ver='v1', data=None, **kwargs):
        """ Extends base class method to handle DNA Center JSON data """
        # Construct URL, serialize data and send request
        url = self.base_url + '/api/' + ver + '/' + api.strip('/')
        data = json.dumps(data).encode('utf-8') if data is not None else None
        response = super(Dnac, self).request(method, url, data=data, **kwargs)
        # Return requests.Response object if content is not JSON
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type.lower():
            logging.debug('Not decoding ' + content_type)
            response.raise_for_status()  # Raise HTTPError, if one occurred
            return response
        # Otherwise deserialize data and return JsonObj object
        json_obj = response.json(object_hook=JsonObj)
        if 400 <= response.status_code < 600 and 'response' in json_obj:
            # Use DNA Center returned error message in case of HTTP error
            response.reason = _flatten(': ', json_obj.response,
                                       ['errorCode', 'message', 'detail'])
        response.raise_for_status()  # Raise HTTPError, if one occurred
        return json_obj

    def wait_on_task(self, task_id, timeout=125, interval=2, backoff=1.15):
        """ Repeatedly requests DNA Center task status until completed """
        start_time = time.time()
        while True:
            # Get task status by id
            response = self.get('task/' + task_id)
            if 'endTime' in response.response:  # Task has completed
                msg = _flatten(': ', response.response,
                               ['errorCode', 'failureReason', 'progress'])
                # Raise exception when isError is true else log completion
                if response.response.get('isError', False):
                    raise TaskError(msg, response=response)
                else:
                    logging.info('TASK %s has completed and returned: %s'
                                 % (task_id, msg))
                return response
            elif (start_time + timeout < time.time()):  # Task has timed out
                raise TimeoutError('TASK %s did not complete within the '
                                   'specified time-out (%s seconds)'
                                   % (task_id, timeout))
            logging.info('TASK %s has not completed yet. Sleeping %d seconds'
                         % (task_id, interval))
            time.sleep(int(interval))
            interval *= backoff

class TimeoutError(Exception):
    """ Custom exception raised when a task has timed out """
    pass

class TaskError(Exception):
    """ Custom exception raised when a task has failed """

    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop('response', None)
        super(TaskError, self).__init__(*args, **kwargs)

class JsonObj(dict):
    """ Dictionary with attribute access """

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, name):
        """ x.__getattr__(y) <==> x.y """
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __str__(self):
        """ Serialize object to JSON formatted string with indents """
        return json.dumps(self, indent=4)

def _flatten(string, dct, keys):
    """ Helper function to join values of given keys existing in dict """
    return string.join(str(dct[k]) for k in set(keys) & set(dct.keys()))

def find(obj, val, key='id'):
    """ Recursively search JSON object for a value of a key/attribute """
    if isinstance(obj, list):  # JSON array
        for item in obj:
            r = find(item, val, key)
            if r is not None:
                return r
    elif isinstance(obj, JsonObj):  # JSON object
        if obj.get(key) == val:
            return obj
        for item in iter(obj):
            if isinstance(obj[item], list):
                return find(obj[item], val, key)

def ctime(val):
    """ Convert time in milliseconds since the epoch to a formatted string """
    return time.ctime(int(val) // 1000)
