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
import ipaddress  

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
        # return query result and size of result
        return self.client.query_entities(query)
    
    def get_entity(self, key):
        print("[INF] Getting entity from table")
        return self.client.get_entity(key["PartitionKey"], key["RowKey"])
    
    def delete(self, entity):
        print("[INF] Deleting entity from table")
        self.client.delete_entity(entity["PartitionKey"], entity["RowKey"])

    def create_ip_entity(self, cidr, peering_state, vnet_name, vnet_id, peering_sync_level, subnets, subscription_id, latest_event, location, additional_data):
        print("[INF] Creating IP entity")
        hex_ip = cidr_to_int(cidr)
        if vnet_name == "":
            vnet_is_used = False
        else:
            vnet_is_used = True
        entity = {
            "PartitionKey": hex_ip,
            "RowKey": hashlib.md5(hex_ip.encode()).hexdigest(),
            "IP": cidr,
            "AddressCount": ip_mask[int(cidr.split('/')[1])],
            "Used": vnet_is_used,
            "PeeringState": peering_state,
            "VNetName": vnet_name,
            "VNetID": vnet_id,
            "PeeringSyncLevel": peering_sync_level,
            "Subnets": subnets,
            "SubscriptionID": subscription_id,
            "LatestEvent": latest_event,
            "Location": location,
            "AdditionalData": additional_data
        }
        self.upsert(entity)
    def get_ip_entity(self, cidr):
        try:
            result = self.get_entity({"PartitionKey": cidr_to_int(cidr), "RowKey": hashlib.md5(cidr_to_int(cidr).encode()).hexdigest()})
        except Exception as e:
            return "",False
        return result,True
    
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
    queue_name = os.environ.get("QUEUE_NAME", "")
    default_subscription = os.environ.get("DEFAULT_SUBSCRIPTION", "00000000-0000-0000-0000-000000000000")
    hub_id = os.environ.get("HUB_ID","")
    debug = True
    
    cred = DefaultAzureCredential()

    ips_table = TableClient(storage_name, os.environ.get("TABLE_NAME", "ips"), cred)
    system_table = TableClient(storage_name, "system", cred)
    az_client = AzClient(default_subscription, cred)

    result = ips_table.query("Used eq false and AddressCount eq {size}".format(size = ip_mask[16]))

    match os.environ.get("JOB_ROLE").lower():
        case "collector":
            if queue_name == "":
                queue_name = "virtualnetworkpeerings"
            queue = QueueClient(storage_name, cred)
            subscriptions_map = {}
            for item in queue.receive(queue_name):
                event = json.loads(item)
                match event.get("eventType"):
                    case "Microsoft.Resources.ResourceWriteSuccess":
                        if hub_id == "" or hub_id not in event.get("subject"):
                            hub_id = event.get("subject").split('/virtualNetworkPeerings/')[0]
                            system_table.upsert({"PartitionKey": default_subscription, "RowKey": "","Value":hub_id})
                        peering_info, fail = az_client.get_resource_by_id(event.get("subject"),"2024-01-01")
                        if peering_info != "" and not fail:  
                            vnet_info, fail = az_client.get_resource_by_id(peering_info.properties["remoteVirtualNetwork"]["id"],"2024-01-01")
                            if vnet_info != "" and not fail:
                                for ip in vnet_info.properties["addressSpace"]["addressPrefixes"]:
                                    subnets = {}
                                    for subnet in vnet_info.properties["subnets"]:
                                        subnets[subnet["name"]] = subnet["properties"]["addressPrefixes"][0]
                                    subscription_id = vnet_info.id.split('/')[2]
                                    subscription_info, fail = az_client.get_resource_by_id("/subscriptions/" + subscription_id, "2022-12-01")
                                    if not fail:
                                        subscription_name = subscription_info.additional_properties["displayName"]
                                        subscriptions_map[subscription_id] = subscription_name
                                    else:
                                        subscription_name = "Unknown"
                                    ips_table.create_ip_entity(ip, peering_info.properties["peeringState"], vnet_info.name, vnet_info.id, peering_info.properties["peeringSyncLevel"], json.dumps(subnets), subscription_id, event.get("eventType"), vnet_info.location, "")
                                    #ips_table.upsert({"PartitionKey":  available_ip_num, "RowKey":hashlib.md5(available_ip_num.encode()).hexdigest(), "IP": ip, "AddressCount":ip_mask[int(ip.split('/')[1])], "Used":True,"PeeringState": peering_info.properties["peeringState"], "VNetName": vnet_info.name,"VNetID": vnet_info.id,"PeeringSyncLevel": peering_info.properties["peeringSyncLevel"],"Subnets": json.dumps(subnets),"SubscriptionID": subscription_id, "LatestEvent":event.get("eventType"),"Location":vnet_info.location,"AdditionalData":"","Disabled":False})
            for key in subscriptions_map:
                system_table.upsert({"PartitionKey": key, "RowKey": "","Value":subscriptions_map[key]})
        case "initiator":
            spoke_ips = os.environ.get("SPOKE_IP_RANGES","")
            if hub_id =="":
                hub_id = system_table.get_entity({"PartitionKey": default_subscription, "RowKey": ""}).get("Value")
                if hub_id == "":
                    print("[ERR] Hub ID not found")
                    return
            if spoke_ips == "":
                hub_info, fail = az_client.get_resource_by_id(hub_id, "2024-01-01")
                if fail:
                    print("[ERR] Hub not found")
                    return
                if hub_info.tags["SpokeAddressPrefixes"] == "":
                    print("[ERR] Spoke IP ranges not found")
                    return
                spoke_ips = hub_info.tags["SpokeAddressPrefixes"]
            for ip in spoke_ips.split(','):
                result, exists = ips_table.get_ip_entity(ip)
                if not exists:
                    ips_table.create_ip_entity(ip, "", "", "", "", "", "", "", "","")
                else:
                    print("[INF] Record already exists: " + str(result))
        case "allocator":
            if queue_name == "":
                queue_name = "ipsallocation"
            queue = QueueClient(storage_name, cred)
            for item in queue.receive(queue_name, recieve_only=debug):
                event = json.loads(item)
                vnet_subscription = event.get("SubscriptionID")
                vnet_name = event.get("VNetName")
                match event.get("eventType"):
                    case "Custom.IP.Allocation":
                        requested_size = int(event.get("mask"))
                        query_size = requested_size
                        while query_size > 1:
                            print("[INF] Searching for IP with size: " + str(query_size))
                            result = ips_table.query("Used eq false and AddressCount eq {size}".format(size = ip_mask[query_size]))
                            try :
                                next_result = result.next()
                                ips_table.upsert({"PartitionKey": next_result["PartitionKey"], "RowKey": next_result["RowKey"], "Used": True, "VNetName": vnet_name, "SubscriptionID": vnet_subscription, "LatestEvent": event.get("eventType")})
                                break
                            except:
                                next_result = []
                            if len(next_result) > 0:
                                # Split the IP range to requested size and update the table. Should mark original IP as disabled, create new IPs with the split range and store their parent key into ChildKeys
                                # Should repeat splitting until the requested_size is reached
                                cidr = next_result["IP"]
                                network = ipaddress.ip_network(cidr, strict=False)  
                                child_keys = []
                                for ip in network.subnets(new_prefix=requested_size):
                                    ips_table.create_ip_entity(str(ip), "", "", "", "", "", "", "", "","")
                                    child_keys.append(cidr_to_int(str(ip)))
                                ips_table.upsert({"PartitionKey": cidr_to_int(cidr), "RowKey": hashlib.md5(cidr_to_int(cidr).encode()).hexdigest(), "ChildKeys": ",".join(child_keys),"Used":True})
                                query_size = requested_size
                                break
                            else:
                                query_size -= 1
                    case "Custom.IP.Release":
                        pass
            for ip in ips_table.query("ChildrenKeys gt '0'"):
                print(ip)

main()