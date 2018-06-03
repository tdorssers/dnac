"""
Script to display SDA segments
"""

from __future__ import print_function
import dna
import logging

HOST = ""
USERNAME = ""
PASSWORD = ""
LOGGING = True

def main():
    if LOGGING:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
    with dna.Dnac(HOST) as dnac:
        dnac.login(USERNAME, PASSWORD)
        domains = dnac.get("data/customer-facing-service/ConnectivityDomain",
                           ver="v2")
        segments = dnac.get("data/customer-facing-service/Segment", ver="v2")
        fmt = "{:4} {:26} {:13} {:7} {:26}"
        print(fmt.format("VLAN", "Name", "Traffic type", "Layer 2", "Fabric"))
        print('-'*80)
        for segment in segments.response:
            fabric = dna.find(domains, segment.connectivityDomain.idRef).name
            print(fmt.format(segment.vlanId, segment.name, segment.trafficType,
                             str(segment.isFloodAndLearn), fabric))
        print('='*80)

if __name__ == "__main__":
    main()
