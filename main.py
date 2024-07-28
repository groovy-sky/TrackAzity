from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueServiceClient,BinaryBase64DecodePolicy
from azure.data.tables import TableServiceClient,UpdateMode
from azure.mgmt.resource import ResourceManagementClient
import os
import base64
import json
import hashlib
import socket  
import struct  

ip_mask = {  
    1: 2147483648,  
    2: 1073741824,  
    3: 536870912,  
    4: 268435456,  
    5: 134217728,  
    6: 67108864,  
    7: 33554432,  
    8: 16777216,  
    9: 8388608,  
    10: 4194304,  
    11: 2097152,  
    12: 1048576,  
    13: 524288,  
    14: 262144,  
    15: 131072,  
    16: 65536,  
    17: 32768,  
    18: 16384,  
    19: 8192,  
    20: 4096,  
    21: 2048,  
    22: 1024,  
    23: 512,  
    24: 256,  
    25: 128,  
    26: 64,  
    27: 32,  
    28: 16,  
    29: 8,  
    30: 4,  
    31: 2,  
    32: 1  
}  

def cidr_to_int(cidr):  
    ip, prefix = cidr.split('/')  
    ip_long = struct.unpack("!L", socket.inet_aton(ip))[0]  
    return hex((ip_long << 32) + ip_mask[int(prefix)])  

class AzClient:
    def __init__(self, subscription_id, credential):
        print("[INF] Initializing Azure REST API Client")
        self.credential = credential
        self.subscription_id = subscription_id
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)

    def set_subscription(self, subscription_id):
        print("[INF] Changing subscription ID")
        self.subscription_id = subscription_id

    def set_credentials(self, credential):
        print("[INF] Changing credentials")
        self.credential = credential
    
    def get_resource(self, resource_group, resource_namespace, resource_type, resource_name, api_version):
        response = self.resource_client.resources.get(
        resource_group_name=resource_group,
        resource_provider_namespace=resource_namespace,
        parent_resource_path="",
        resource_type=resource_type,
        resource_name=resource_name,
        api_version=api_version)
        return response

    def get_resource_by_id(self, resource_id, api_ver=None):
        failed = False
        if api_ver is None:
            api_ver = self.get_provider_latest_api_version(resource_id.split('/')[6], resource_id.split('/')[7])
        try:
            response = self.resource_client.resources.get_by_id(resource_id, api_version=api_ver)
        except Exception as e:
            print("[ERR]" + str(e))
            response = ""
            failed = True
        return response,failed

    def deploy_template(self, resource_group, template_file, parameters):
        print("[INF] Deploying template")
        with open(template_file, "r") as file:
            template_body = json.load(file)

        # Create a unique deployment name from the current timestamp and template's name without extension
        deployment_prefix = os.path.splitext(template_file)[0]

        deployment_name = deployment_prefix + "-" + str(int(time.time()))

        deployment_properties = {
            "properties": {
            "template": template_body,
            "parameters": parameters,
            "mode": DeploymentMode.incremental}
        }

        deployment_result = self.resource_client.deployments.begin_create_or_update(
            resource_group,
            deployment_name,
            deployment_properties
        )

        # Check deployment status and wait till it's done
        deployment_result.wait()
        return deployment_result.result().properties.provisioning_state
    
    def get_provider(self, provider_namespace):
        return self.resource_client.providers.get(provider_namespace)

    def get_provider_latest_api_version(self, provider_namespace, resource_type):
        for resource in self.get_provider(provider_namespace).resource_types:
            if resource.resource_type == resource_type:
                return resource.api_versions[0]

class TableClient:
    def __init__(self, account, table, credential):
        print("[INF] Initializing Azure Table Client")
        url = "https://" + account + ".table.core.windows.net"
        self.client = TableServiceClient(endpoint=url, credential=credential).get_table_client(table)

    def upsert(self, entity):
        print("[INF] Inserting entity into table")
        self.client.upsert_entity(mode=UpdateMode.MERGE,entity=entity)

    def query(self, query):
        print("[INF] Querying table")
        return self.client.query_entities(query)
    
    def delete(self, entity):
        print("[INF] Deleting entity from table")
        self.client.delete_entity(entity["PartitionKey"], entity["RowKey"])

class QueueClient:
    def __init__(self, account, credential):
        print("[INF] Initializing Azure Queue Client")
        url = "https://" + account + ".queue.core.windows.net"
        self.client = QueueServiceClient(account_url=url, credential=credential,  message_decode_policy=BinaryBase64DecodePolicy())

    def receive(self, queue_name, recieve_only = False):
        print("[INF] Receiving messages from queue")
        response = []
        queue = self.client.get_queue_client(queue_name)
        for message in queue.receive_messages():
            response.append(base64.b64decode(message.content))
            if recieve_only:
                queue.delete_message(message)
        return response

    def send(self, queue_name, message):
        print("[INF] Sending message to queue")
        queue_client = self.client.get_queue_client(queue_name)
        queue_client.send_message(message)

def main():
    storage_name = os.environ.get("STORAGE_NAME")
    queue_name = os.environ.get("QUEUE_NAME") 
    table_name = os.environ.get("TABLE_NAME")
    default_subscription = "00000000-0000-0000-0000-000000000000"

    cred = DefaultAzureCredential()

    queue = QueueClient(storage_name, cred)
    table = TableClient(storage_name, table_name, cred)    
    az_client = AzClient(default_subscription, cred)
    for item in queue.receive(queue_name):
        event = json.loads(item)
        match event.get("eventType"):
            case "Microsoft.Resources.ResourceWriteSuccess":
                peering_info, fail = az_client.get_resource_by_id(event.get("subject"),"2024-01-01")
                if peering_info != "" and not fail:  
                    vnet_info, fail = az_client.get_resource_by_id(peering_info.properties["remoteVirtualNetwork"]["id"],"2024-01-01")
                    if vnet_info != "" and not fail:
                        for ip in vnet_info.properties["addressSpace"]["addressPrefixes"]:
                            available_ip_num = cidr_to_int(ip)[2:]
                            subnets = {}
                            for subnet in vnet_info.properties["subnets"]:
                                subnets[subnet["name"]] = subnet["properties"]["addressPrefixes"][0]
                            subscription_id = vnet_info.id.split('/')[2]
                            subscription_info, fail = az_client.get_resource_by_id("/subscriptions/" + subscription_id, "2022-12-01")
                            if not fail:
                                subscription_name = subscription_info.additional_properties["displayName"]
                            else:
                                subscription_name = "Unknown"
                            table.upsert({"PartitionKey":  available_ip_num, "RowKey":hashlib.md5(available_ip_num.encode()).hexdigest(), "IP": ip, "AddressCount":ip_mask[int(ip.split('/')[1])], "IsInUse":True,"PeeringState": peering_info.properties["peeringState"], "VNetName": vnet_info.name,"VNetID": vnet_info.id,"PeeringSyncLevel": peering_info.properties["peeringSyncLevel"],"Subnets": json.dumps(subnets),"SubscriptionID": subscription_id, "SubscriptionName": subscription_name,"LatestEvent":event.get("eventType"),"Location":vnet_info.location})

main()