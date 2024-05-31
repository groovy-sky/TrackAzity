from azure.identity import ClientSecretCredential
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
import sys, csv

def parseResourceId(resourceId):
    parts = resourceId.split('/')
    return {
        "subscriptionId": parts[2],
        "resourceGroup": parts[4],
        "resourceType": parts[6],
        "resourceName": parts[8]
    }

def generateCSV(data,filename):

    with open(filename, mode='w') as csv_file:
        fieldnames = ['IP','subscriptionId','vnetName', 'peeringState', 'peeringSyncLevel']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writeheader()
        for row in data:
            writer.writerow(row)

def main():
    # Reads user input for resource ID
    resourceId = sys.argv[1]

    parsed = parseResourceId(resourceId)

    # https://pypi.org/project/azure-identity/
    resource_client = ResourceManagementClient(
        credential=DefaultAzureCredential(),
        subscription_id=parsed["subscriptionId"]
    )

    # Get information about the resource and store in a dictionary
    result = resource_client.resources.get_by_id(resource_id=resourceId, api_version="2024-01-01")
    peeringsDict = {}
    for peering in result.properties["virtualNetworkPeerings"]:
        spoke_id = peering["properties"]["remoteVirtualNetwork"]["id"]
        spoke_parsed = parseResourceId(spoke_id)
        spoke_subscription_id = spoke_parsed["subscriptionId"]
        spoke_vnet_name = spoke_parsed["resourceName"]
        for ip in peering["properties"].get("remoteAddressSpace").get("addressPrefixes"):
            peeringInfo = {
                "subscriptionId": spoke_subscription_id,
                "vnetName": spoke_vnet_name,
                "peeringState": peering["properties"]["peeringState"],
                "peeringSyncLevel": peering["properties"]["peeringSyncLevel"]
            }
            peeringsDict[ip] = peeringInfo
    print(peeringsDict)
    
    # Store peeringsDict to output.csv file
    with open('output.csv', mode='w', newline='') as csv_file:
        fieldnames = ['IP', 'subscriptionId', 'vnetName', 'peeringState', 'peeringSyncLevel']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter='\x1f')
        writer.writeheader()
        for ip, peeringInfo in peeringsDict.items():
            writer.writerow({'IP': ip, 'subscriptionId': peeringInfo['subscriptionId'], 'vnetName': peeringInfo['vnetName'], 'peeringState': peeringInfo['peeringState'], 'peeringSyncLevel': peeringInfo['peeringSyncLevel']})


if __name__ == "__main__":
    main()