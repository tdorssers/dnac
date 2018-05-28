# dnac

Module `dna.py` implements a northbound API client manager for Cisco DNA Center.

Basic Usage:
```
  dnac = dna.Dnac('https://10.0.0.1/')
  dnac.login('admin', 'password')
  print(dnac.get('network-device/count'))
  dnac.close()
```
Or as a context manager:
```
  with dna.Dnac('https://10.0.0.1/') as dnac:
      dnac.login('admin', 'password')
      print(dnac.get('network-device/count'))
```
## Sample scripts

* `segment.py` displays SDA segments
* `pool-import.py` adds global IP pools and assigns them to virtual networks from csv file
* `cfs-import.py` configures Campus fabric edge ports from a csv file
* `template.py` provisions a user template without the use of network profiles
