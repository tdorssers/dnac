# dnac

Module `dna.py` implements a northbound API client manager for Cisco DNA Center. It uses Python `requests` to perform API calls.

Basic Usage:
```
  dnac = dna.Dnac('10.0.0.1')
  dnac.login('admin', 'password')
  print(dnac.get('network-device/count'))
  dnac.close()
```
Or as a context manager:
```
  with dna.Dnac('10.0.0.1') as dnac:
      dnac.login('admin', 'password')
      print(dnac.get('network-device/count'))
```
DNAC exception raising example:
```
>>> print(dnac.put('network-device/count'))

Traceback (most recent call last):
...
HTTPError: 500 Server Error: Unexpected error: Unexpected error: Request method 'PUT' not supported
>>>
```
## Sample scripts

* `segment.py` displays SDA segments
* `pool-import.py` adds global IP pools and assigns them to virtual networks from csv file
* `cfs-import.py` configures Campus fabric edge ports from a csv file
* `template.py` provisions a user template without the use of network profiles
