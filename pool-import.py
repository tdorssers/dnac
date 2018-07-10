""" Script to add root and reserve sub IP pools from a csv file """

from __future__ import print_function
import json
import logging
import csv
import re
import dna

HOST = ""
USERNAME = ""
PASSWORD = ""
CSVFILE = "pool-import.csv"
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

def make_list(s):
    """ Split on whitespace and comma """
    return re.split(r'[\s,]+', s) if s is not '' else []

def make_bool(s):
    """ Convert string to bool """
    return True if s.lower() == 'true' else False

def main():
    if LOGGING:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
    with open(CSVFILE) as csvfile:
        rows = [row for row in csv.DictReader(csvfile, delimiter=DELIMIT)]
    with dna.Dnac(HOST) as dnac:
        dnac.login(USERNAME, PASSWORD)
        # Get fabric domains, virtual networks and virtual network contexts
        ippools = dnac.get("ippool", ver="v2").response
        sites = dnac.get("group", params={"groupType": "SITE"}).response
        for row in rows:
            parent = lookup(ippools, "ipPoolName", row["Parent Pool"])
            site = lookup(sites, "groupNameHierarchy", row["Site"])
            # Reserve sub pool
            if parent is not None:
                print("Reserving %s" % row["IP Pool Name"])
                # Request body for new sub pool
                data = {"ipPoolName": row["IP Pool Name"],
                        "ipPoolOwner": "DNAC",
                        "ipPoolCidr": row["IP Pool CIDR"],
                        "parentUuid": parent.id,
                        "shared": True,
                        "overlapping": make_bool(row["Overlapping"]),
                        "context": [{"contextKey": "siteId",
                                     "contextValue": site.id}],
                        "dhcpServerIps": make_list(row["DHCP Servers"]),
                        "dnsServerIps": make_list(row["DNS Servers"]),
                        "gateways": make_list(row["Gateway"])}
                # Commit request
                logging.debug("data=" + json.dumps(data))
                response = dnac.post("ippool/subpool", ver="v2",
                                     data=data).response
                print("Waiting for Task")
                task_result = dnac.wait_on_task(response.taskId).response
                print("Completed in %s seconds" % (float(task_result.endTime
                                                   - task_result.startTime)
                                                   / 1000))
                # Make object reference for GUI
                data = [{"groupUuid": site.id,
                         "instanceType": "reference",
                         "key": "ip.pool.%s.%s" % (row["Type"].lower(),
                                                   task_result.progress),
                         "namespace": "global",
                         "type": "reference.setting",
                         "value": [{"objReferences": [task_result.progress],
                                    "type": row["Type"].lower(),
                                    "url": ""}]}]
                # Commit request
                logging.debug("data=" + json.dumps(data))
                response = dnac.post("commonsetting/global/" + site.id,
                                     data=data).response
                print("Waiting for Task")
                task_result = dnac.wait_on_task(response.taskId).response
                print("Completed in %s seconds" % (float(task_result.endTime
                                                   - task_result.startTime)
                                                   / 1000))
            # Create root pool
            else:
                print("Adding %s" % row["IP Pool Name"])
                # Request body for new IP pool
                data = dna.JsonObj({"ipPoolCidr": row["IP Pool CIDR"],
                            "ipPoolName": row["IP Pool Name"],
                            "dhcpServerIps": make_list(row["DHCP Servers"]),
                            "dnsServerIps": make_list(row["DNS Servers"]),
                            "gateways": make_list(row["Gateway"]),
                            "overlapping": make_bool(row["Overlapping"])})
                # Commit request
                logging.debug("data=" + json.dumps(data))
                response = dnac.post("ippool", ver="v2", data=data).response
                print("Waiting for Task")
                task_result = dnac.wait_on_task(response.taskId).response
                print("Completed in %s seconds" % (float(task_result.endTime
                                                   - task_result.startTime)
                                                   / 1000))
                # Task result returns new ip pool id
                data.id = task_result.progress
                ippools.append(data)

if __name__ == "__main__":
    main()
