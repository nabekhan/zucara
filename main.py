"""
This script counts the number of TBR events for a patient. It must:
1) Parse the NS list to retrieve pts
2) Retrieve and review data from NS
3) Export results to csv
"""

import csv
import requests
from datetime import datetime


def jsonurl(ns_uuid, startDate, endDate):
    base_url = f"https://_cgm:queries_@{ns_uuid}.cgm.bcdiabetes.ca/get-glucose-data"
    #base_url = f"https://_cgm:queries_@9076ffe8-cd66-5d09-b358-4985b625cb7d.cgm.bcdiabetes.ca/get-glucose-data"
    params = {
        "gte": f"{startDate}Z",
        "lte": f"{endDate}Z"
    }
    query_string = f"gte={params['gte']}&lte={params['lte']}"
    full_url = f"{base_url}?{query_string}"
    return full_url

def dataretrieve(ns_uuid, startDate, endDate):
    url = jsonurl(ns_uuid, startDate, endDate)
    auth = ('_cgm', 'queries_')  # Authentication credentials
    response = requests.get(url, auth=auth)
    # Print the final URL being used for the request
    print("Request URL:", response.url)
    response.raise_for_status()  # Check if the request was successful
    data = response.json()
    data = sorted(data, key=lambda d: d['date']) # sort data from first to last date
    print(data)
    return data, response.url

def cgmtype(device):
    if "lvconnect" in device:
        return "libre"
    else:
        return "dexcom"


def main(nsstatusfile, startDate, endDate):
    results = [["ID", "pt_link", "ns_uuid", "entries", "nsurl", "tbrcount"]]
    # open nsstatus file
    with open(nsstatusfile, mode="r") as nsstatus:
        readfile = csv.reader(nsstatus)
        for index, row in enumerate(readfile):
            print(f"On Row {index}")
            if index == 0:
                IDindex = row.index("ID")
                pt_linkindex = row.index("pt_link")
                ns_uuidindex = row.index("ns_uuid")
            else:
                data, responseurl = dataretrieve(row[ns_uuidindex], startDate, endDate)
                if data:
                    try:
                        retrievedevice = data[0]['device']
                    except:
                        retrievedevice = ""
                    cgm = cgmtype(retrievedevice)
                    tbrcount = 0
                    # this logic checks for tbr counts. it filters for poor data
                    for index, content in enumerate(data):
                        # on first row, initialize variables based on cgm type
                        if index == 0:
                            previous_entry = content
                            tbrnumber = 0
                            if cgm == "libre":
                                maxGap = 18
                                tbrthreshold = 2
                            else:
                                maxGap = 7
                                tbrthreshold = 3
                            continue
                        # get the time difference between the last two readings
                        else:
                            timeDelta = (datetime.fromisoformat(content["dateString"].split(".")[0]) - datetime.fromisoformat(
                                previous_entry["dateString"].split(".")[0])).total_seconds() / 60

                            # if the difference in the two readings is odd, skip it
                            if (timeDelta < 2) or (timeDelta > maxGap):
                                previous_entry = content
                                continue

                            # if the time is good, take the reading and see if its below threshold
                            cgmreading = float(content["sgv"])
                            previous_entry = content
                            if cgmreading < 54:
                                print(content["dateString"].split(".")[0], cgmreading, cgm, tbrnumber)
                                tbrnumber += 1

                            # if there are enough readings, add to total count, and reset number
                            else:
                                if tbrnumber >= tbrthreshold:
                                    tbrcount += 1
                                tbrnumber = 0
                    print(f"TBR Count: {tbrcount}")
                    result = [row[IDindex], row[pt_linkindex], row[ns_uuidindex], responseurl, "https://"+row[ns_uuidindex]+".cgm.bcdiabetes.ca/report/", tbrcount]
                    results.append(result)
                    print(result)
    with open(f"gitignore/{startDate}_{endDate}_results.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(results)


if __name__ == "__main__":
    main("gitignore/ns_status_all-2024-08-05_12-52-15.csv", "2024-07-05", "2024-08-05")