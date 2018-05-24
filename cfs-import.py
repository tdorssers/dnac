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
DELIMIT = ";"
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
                        ver="v2").response
        segments = dnac.get("data/customer-facing-service/Segment",
                            ver="v2").response
        # Iterate unique hostnames
        for host in set(r["Hostname"] for r in rows if r["Hostname"] != ""):
            print("Host:", host)
            new_diis = []
            removed = []
            updated = []
            added = []
            # Lookup device matching hostname
            device = dna.find(devices, host, "hostname")
            # Get interfaces and device info
            ifs = dnac.get("interface/network-device/" + device.id).response
            di = dnac.get("data/customer-facing-service/DeviceInfo",
                          ver="v2", params={"name": device.id}).response[0]
            # Build list of already configured interface ids
            if_ids = [i.interfaceId for i in di.deviceInterfaceInfo]
            # Iterate csv file rows for this host
            for row in [r for r in rows if r["Hostname"] == host]:
                data = None
                # Lookup objects matching name specified in csv file rows
                interface = lookup(ifs, "portName", row["Interface"])
                auth = lookup(sps, "name", row["Authentication"])
                sgt = lookup(sgts, "name", row["Scalable group"])
                segment = lookup(segments, "name", row["Data segment"])
                voice = lookup(segments, "name", row["Voice segment"])
                # Remove interface if no values are specified
                if not any((auth, sgt, segment, voice)):
                    try:
                        if_ids.remove(interface.id)
                    except ValueError:
                        raise(InputError(interface.portName + " not in cfs"))
                    removed.append(interface.portName)
                # Update interface if id is found in list
                elif interface.id in if_ids:
                    if_ids.remove(interface.id)
                    updated.append(interface.portName)
                    # Pop interface info from list and store in data dict
                    for idx, dii in enumerate(di.deviceInterfaceInfo):
                        if dii.interfaceId == interface.id:
                            data = di.deviceInterfaceInfo.pop(idx)
                            break
                    # Clear fields
                    data.segment = []
                    data.pop("authenticationProfile", None)
                    data.pop("scalableGroupId", None)
                # Add interface
                else:
                    added.append(interface.portName)
                    data = dna.JsonObj({"interfaceId": interface.id,
                                        "role": "LAN", "segment": [],
                                        "connectedToSubtendedNode": False})
                # Update fields
                if auth is not None:
                    data.authenticationProfileId = auth.siteProfileUuid
                if segment is not None:
                    data.segment.append({"idRef": segment.id})
                if voice is not None:
                    data.segment.append({"idRef": voice.id})
                if sgt is not None:
                    data.scalableGroupId = sgt.id
                # Save in device interface info list
                if data is not None:
                    new_diis.append(data)
            # Replace all keys by an idRef key for untouched interfaces
            refs = [{"idRef": i.id} for i in di.deviceInterfaceInfo
                    if i.interfaceId in if_ids]
            # Save updated device interface info
            di.deviceInterfaceInfo = refs + new_diis
            print("Removed:", *removed)
            print("Updated:", *updated)
            print("Added:", *added)
            # Commit changes
            logging.debug("data=" + json.dumps([di]))
            response = dnac.put("data/customer-facing-service/DeviceInfo",
                                ver="v2", data=[di]).response
            print("Waiting for Task")
            task_result = dnac.wait_on_task(response.taskId).response
            print("Completed in %s seconds" % (float(task_result.endTime
                                               - task_result.startTime) / 1000))

if __name__ == "__main__":
    main()
