""" Script to add global IP pools assigned to virtual networks from csv file """

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
        domains = dnac.get("data/customer-facing-service/ConnectivityDomain",
                           ver="v2").response
        vns = dnac.get("data/customer-facing-service/VirtualNetwork",
                       ver="v2").response
        vncs = dnac.get("data/customer-facing-service/virtualnetworkcontext",
                        ver="v2").response
        for row in rows:
            print("Adding %s" % row["IP Pool Name"])
            # Lookup objects matching name specified in csv file rows
            domain = lookup(domains, "name", row["Fabric"])
            vnc = lookup(vncs, "name", row["Virtual Network"])
            vn = next(v for v in vns if v.namespace == domain.id
                      and v.virtualNetworkContextId == vnc.id)
            # Request body for new IP pool
            data = {"ipPoolCidr": row["IP Pool CIDR"],
                    "ipPoolName": row["IP Pool Name"],
                    "dhcpServerIps": make_list(row["DHCP Servers"]),
                    "dnsServerIps": make_list(row["DNS Servers"]),
                    "gateways": make_list(row["Gateway"]),
                    "overlapping": make_bool(row["Overlapping"])}
            # Commit request
            logging.debug("data=" + json.dumps(data))
            response = dnac.post("ippool", ver="v2", data=data).response
            print("Waiting for Task")
            task_result = dnac.wait_on_task(response.taskId).response
            print("Completed in %s seconds" % (float(task_result.endTime
                                               - task_result.startTime) / 1000))
            # Segment name is composed of CIDR and VN
            name = (row["IP Pool CIDR"].split('/')[0].replace('.', '_') + '-'
                    + row["Virtual Network"])
            print("Adding %s" % name)
            # Object for updated virtual network
            data = {"type": "Segment", "name": name,
                    "trafficType": row["Traffic Type"],
                    "ipPoolId": task_result.progress,
                    "isFloodAndLearn": make_bool(row["Layer 2"]),
                    "isApProvisioning": make_bool(row["AP Provision"]),
                    "isDefaultEnterprise": False,
                    "connectivityDomain": {"idRef": domain.id}}
            # Append to segment list
            vn.segment.append(data)
            # Commit request
            logging.debug("data=" + json.dumps([vn]))
            response = dnac.put("data/customer-facing-service/VirtualNetwork",
                                ver="v2", data=[vn]).response
            print("Waiting for Task")
            task_result = dnac.wait_on_task(response.taskId).response
            print("Completed in %s seconds" % (float(task_result.endTime
                                               - task_result.startTime) / 1000))

if __name__ == "__main__":
    main()
