from azure.identity import ClientSecretCredential
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
import sys

def parseResourceId(resourceId):
    parts = resourceId.split('/')
    return {
        "subscriptionId": parts[2],
        "resourceGroup": parts[4],
        "resourceType": parts[6],
        "resourceName": parts[8]
    }
def main():
    # Reads user input for resource ID
    resourceId = sys.argv[1]

    parsed = parseResourceId(resourceId)

    # https://pypi.org/project/azure-identity/
    resource_client = ResourceManagementClient(
        credential=DefaultAzureCredential(),
        subscription_id=parsed["subscriptionId"]
    )

    # Check resource existence
    result = resource_client.resources.get_by_id(
        resource_id=resourceId, api_version="2024-01-01")
    print(result)


if __name__ == "__main__":
    main()