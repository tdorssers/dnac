""" Script to configure Campus fabric edge ports from a csv file """

from __future__ import print_function
import logging
import json
import csv
import dna

HOST = ""
USERNAME = ""
PASSWORD = ""
CSVFILE = "cfs-import.csv"
DELIMIT = ","
LOGGING = True

def lookup(list_dicts, key, val):
    """ Find key by value in list of dicts and return dict """
    if val == "":
        return None
    r = next((d for d in list_dicts if d[key] == val), None)
    if r is None:
        raise(ValueError(val + " not found"))
    return r

def main():
    if LOGGING:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
    with open(CSVFILE) as csvfile:
        rows = [row for row in csv.DictReader(csvfile, delimiter=DELIMIT)]
    with dna.Dnac(HOST) as dnac:
        dnac.login(USERNAME, PASSWORD)
        # Get devices, auth templates, scalable groups and segments
        devices = dnac.get("network-device")
        sps = dnac.get("siteprofile", params={"populated": "true"}).response
        sgts = dnac.get("data/customer-facing-service/scalablegroup",
                        ver="api/v2").response
        segments = dnac.get("data/customer-facing-service/Segment",
                            ver="api/v2").response
        # Iterate unique hostnames
        for host in set(r["Hostname"] for r in rows if r["Hostname"] != ""):
            print("Host:", host)
            removed = []
            updated = []
            added = []
            # Lookup device matching hostname
            device = dna.find(devices, host, "hostname")
            # Get interfaces and device info
            ifs = dnac.get("interface/network-device/" + device.id).response
            try:
                # DNAC 1.1 uses network device id as cfs name
                di = dnac.get("data/customer-facing-service/DeviceInfo", ver="api/v2",
                              params={"name": device.id}).response[0]
            except IndexError:
                # DNAC 1.2 uses network device hostname as cfs name
                di = dnac.get("data/customer-facing-service/DeviceInfo", ver="api/v2",
                              params={"name": device.hostname}).response[0]
            # Iterate csv file rows for this host
            for row in [r for r in rows if r["Hostname"] == host]:
                data = None
                # Lookup objects matching name specified in csv file rows
                interface = lookup(ifs, "portName", row["Interface"])
                auth = lookup(sps, "name", row["Authentication"])
                sgt = lookup(sgts, "name", row["Scalable group"])
                segment = lookup(segments, "name", row["Data segment"])
                voice = lookup(segments, "name", row["Voice segment"])
                # Pop interface info from list and store in data dict
                for idx, dii in enumerate(di.deviceInterfaceInfo):
                    if dii.interfaceId == interface.id:
                        data = di.deviceInterfaceInfo.pop(idx)
                        break
                # Remove interface action if no values are specified
                if not any((auth, sgt, segment, voice)):
                    removed.append(interface.portName)
                    if data is None:
                        raise(ValueError(interface.portName + " not in cfs"))
                    data = None
                # Update interface action if id is found in list
                elif data is not None:
                    updated.append(interface.portName)
                    # Clear fields
                    data.segment = []
                    data.pop("authenticationProfile", None)
                    data.pop("scalableGroupId", None)
                    data.pop("connectedDeviceType", None)
                # Add interface
                else:
                    added.append(interface.portName)
                    data = dna.JsonObj({"interfaceId": interface.id,
                                        "role": "LAN",
                                        "segment": []})
                # Update fields
                if auth is not None:
                    data.authenticationProfileId = auth.siteProfileUuid
                if segment is not None:
                    data.segment.append({"idRef": segment.id})
                if voice is not None:
                    data.segment.append({"idRef": voice.id})
                if sgt is not None:
                    data.scalableGroupId = sgt.id
                if row["Device type"] != "":
                    data.connectedDeviceType = row["Device type"]
                # Save in device interface info list
                if data is not None:
                    di.deviceInterfaceInfo.append(data)
            print("Removed:", *removed)
            print("Updated:", *updated)
            print("Added:", *added)
            # Commit changes
            logging.debug("data=" + json.dumps([di]))
            response = dnac.put("data/customer-facing-service/DeviceInfo",
                                ver="api/v2", data=[di]).response
            print("Waiting for Task")
            task_result = dnac.wait_on_task(response.taskId).response
            print("Completed in %s seconds" % (float(task_result.endTime
                                               - task_result.startTime) / 1000))

if __name__ == "__main__":
    main()
