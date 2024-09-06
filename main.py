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
import requests

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
        success = True
        if api_ver is None:
            api_ver = self.get_provider_latest_api_version(resource_id.split('/')[6], resource_id.split('/')[7])
        try:
            response = self.resource_client.resources.get_by_id(resource_id, api_version=api_ver)
        except Exception as e:
            print("[ERR]" + str(e))
            response = ""
            success = False
        return response, success

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
    def reserve_ip_entity(self, cidr, vnet_id, location, latest_event, additional_data = ""):
        print("[INF] Reserving IP entity")
        vnet_subscription = vnet_id.split('/')[2]
        vnet_name = vnet_id.split('/')[8]
        hex_ip = cidr_to_int(cidr)
        entity = {
            "PartitionKey": hex_ip,
            "RowKey": hashlib.md5(hex_ip.encode()).hexdigest(),
            "Used": True,
            "SubscriptionID": vnet_subscription,
            "VNetName": vnet_name,
            "VNetID": vnet_id,
            "Location": location,
            "LatestEvent": latest_event,
        }
        if additional_data:
            entity["AdditionalData"] = additional_data
        self.upsert(entity)
    def release_ip_entity(self, cidr):
        print("[INF] Releasing IP entity")
        hex_ip = cidr_to_int(cidr)
        current_entity = self.get_entity({"PartitionKey": hex_ip, "RowKey": hashlib.md5(hex_ip.encode()).hexdigest()})
        entity = {
            "PartitionKey": hex_ip,
            "RowKey": hashlib.md5(hex_ip.encode()).hexdigest(),
            "Used": False,
            "VNetName": "",
            "SubscriptionID": "",
            "LatestEvent": "",
            "AdditionalData": "Released VNetID:" + current_entity.get("VNetID")
        }
        self.upsert(entity)

    def update_additional_data(self, cidr, vnet_id):
        print("[INF] Updating AdditionalData")
        hex_ip = cidr_to_int(cidr)
        entity = self.get_entity({"PartitionKey": hex_ip, "RowKey": hashlib.md5(hex_ip.encode()).hexdigest()})
        if entity:
            entity["AdditionalData"]["VNetID"] = vnet_id
            self.upsert(entity)
    
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
    default_subscription = os.environ.get("DEFAULT_SUBSCRIPTION", "00000000-0000-0000-0000-000000000000")
    hub_id = os.environ.get("HUB_ID","")
    devops_org = os.environ.get("DEVOPS_ORG","")
    devops_webhook = os.environ.get("DEVOPS_WEBHOOK","")
    devops_run = False

    if devops_org != "" and devops_webhook != "":
        devops_url = "https://dev.azure.com/{organization}/_apis/public/distributedtask/webhooks/{webhook}?api-version=6.0-preview".format(organization=devops_org, webhook=devops_webhook)
    debug = False
    
    cred = DefaultAzureCredential()

    ips_table = TableClient(storage_name, os.environ.get("TABLE_NAME", "ips"), cred)
    system_table = TableClient(storage_name, "system", cred)
    az_client = AzClient(default_subscription, cred)

    job_role = os.environ.get("JOB_ROLE").lower()
    job_queue = {"collector":"virtualnetworkpeerings","allocator":"ipsallocation"}[job_role]

    match job_role:
        case "collector":
            queue = QueueClient(storage_name, cred)
            subscriptions_map = {}
            for item in queue.receive(job_queue):
                event = json.loads(item)
                match event.get("eventType"):
                    case "Microsoft.Resources.ResourceWriteSuccess":
                        if hub_id == "" or hub_id not in event.get("subject"):
                            hub_id = event.get("subject").split('/virtualNetworkPeerings/')[0]
                            system_table.upsert({"PartitionKey": default_subscription, "RowKey": "","Value":hub_id})
                        peering_info, ok = az_client.get_resource_by_id(event.get("subject"),"2024-01-01")
                        if peering_info != "" and ok:  
                            vnet_info, ok = az_client.get_resource_by_id(peering_info.properties["remoteVirtualNetwork"]["id"],"2024-01-01")
                            if vnet_info != "" and ok:
                                for ip in vnet_info.properties["addressSpace"]["addressPrefixes"]:
                                    subnets = {}
                                    for subnet in vnet_info.properties["subnets"]:
                                        subnets[subnet["name"]] = subnet["properties"]["addressPrefixes"][0]
                                    subscription_id = vnet_info.id.split('/')[2]
                                    subscription_info, ok = az_client.get_resource_by_id("/subscriptions/" + subscription_id, "2022-12-01")
                                    if ok:
                                        subscription_name = subscription_info.additional_properties["displayName"]
                                        subscriptions_map[subscription_id] = subscription_name
                                    else:
                                        subscription_name = "Unknown"
                                    ips_table.create_ip_entity(ip, peering_info.properties["peeringState"], vnet_info.name, vnet_info.id, peering_info.properties["peeringSyncLevel"], json.dumps(subnets), subscription_id, event.get("eventType"), vnet_info.location, "")
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
                hub_info, ok = az_client.get_resource_by_id(hub_id, "2024-01-01")
                if not ok:
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
            queue = QueueClient(storage_name, cred)
            for item in queue.receive(job_queue, recieve_only=debug):
                event = json.loads(item)
                vnet_subscription = event.get("SubscriptionID")
                vnet_name = event.get("VNetName")
                latest_evnet = event.get("eventType")
                match latest_evnet:
                    case "Custom.IP.Allocation":
                        requested_size = int(event.get("mask"))
                        query_size = requested_size
                        while query_size > 1:
                            print("[INF] Searching for IP with size: " + str(query_size))
                            result = ips_table.query("Used eq false and AddressCount eq {size}".format(size=ip_mask[query_size]))
                            try:
                                next_result = next(result)
                                if query_size == requested_size:
                                    ips_table.reserve_ip_entity(next_result["IP"], vnet_name, vnet_subscription, latest_evnet)
                                else:
                                    # Split the IP range to requested size and update the table. Should mark original IP as disabled, create new IPs with the split range and store their parent key into ChildKeys
                                    cidr = next_result["IP"]
                                    network = ipaddress.ip_network(cidr, strict=False)
                                    child_keys = []
                                    new_size_ip = ""
                                    for ip in network.subnets(new_prefix=requested_size):
                                        ip = str(ip)
                                        ips_table.create_ip_entity(ip, "", "", "", "", "", "", "", "", "")
                                        child_keys.append(cidr_to_int(ip))
                                        new_size_ip = ip
                                    ips_table.upsert({"PartitionKey": cidr_to_int(cidr), "RowKey": hashlib.md5(cidr_to_int(cidr).encode()).hexdigest(), "ChildKeys": ",".join(child_keys), "Used": True})
                                    ips_table.reserve_ip_entity(new_size_ip, vnet_name, vnet_subscription, latest_evnet)
                                    query_size = 1
                            except StopIteration:
                                next_result = []
                            query_size -= 1
                    case "Custom.IP.Release":
                        ips_table.release_ip_entity(event.get("IP"))
                    case "Microsoft.Resources.ResourceWriteSuccess":
                        ip_found = False
                        deployment_info, ok = az_client.get_resource_by_id(event.get("subject"), "2021-04-01")
                        username_email = event.get("data").get("claims").get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn')
                        if ok:
                            vnet_id = deployment_info.properties["outputs"]["vnetId"]["value"]
                            vnet_location = deployment_info.properties["parameters"]["location"]["value"]
                            vnet_size = deployment_info.properties["parameters"]["vnetSize"]["value"]
                            event_time = deployment_info.properties["outputs"]["deployTime"]["value"]
                        if vnet_id != "":
                            subscription_id = vnet_id.split('/')[2]
                            vnet_rg = vnet_id.split('/')[4]
                            vnet_name = vnet_id.split('/')[8]
                        else:
                            print("[ERR] VNet ID not found")
                            return
                        query_size = vnet_size
                        while query_size > 1 and ip_found == False:
                            print("[INF] Searching for IP with size: " + str(query_size))
                            result = ips_table.query("Used eq false and AddressCount eq {size}".format(size=ip_mask[query_size]))
                            try:
                                next_result = next(result)
                                if query_size == vnet_size:
                                    ip_found = True
                                    allocated_ip = next_result["IP"]
                                else:
                                    # Split the IP range to requested size and update the table. Should mark original IP as disabled, create new IPs with the split range and store their parent key into ChildKeys
                                    cidr = next_result["IP"]
                                    network = ipaddress.ip_network(cidr, strict=False)
                                    child_keys = []
                                    allocated_ip = ""
                                    for ip in network.subnets(new_prefix=vnet_size):
                                        ip = str(ip)
                                        ips_table.create_ip_entity(ip, "", "", "", "", "", "", "", "", "")
                                        child_keys.append(cidr_to_int(ip))
                                        allocated_ip = ip
                                    ips_table.upsert({"PartitionKey": cidr_to_int(cidr), "RowKey": hashlib.md5(cidr_to_int(cidr).encode()).hexdigest(), "ChildKeys": ",".join(child_keys), "Used": True})
                                    ip_found = True
                            except StopIteration:
                                next_result = []
                            query_size -= 1
                        # Check for duplicates
                        vnet_ips = 0
                        try:
                            for ip in ips_table.query("VNetName eq '{vnet}' and AdditionalData eq {date}".format(vnet=vnet_name, date=event_time)):
                                vnet_ips += 1
                        except Exception:
                            pass
                        if vnet_ips == 0:
                            ips_table.reserve_ip_entity(allocated_ip, vnet_id, vnet_location, latest_evnet, event_time)
                            message = "az account set -s {subscription};\naz network vnet create -g {rg} -n {vnet} --address-prefix {ip} --subnet-name default --subnet-prefixes {ip}".format(subscription=subscription_id, rg=vnet_rg, vnet=vnet_name,ip = allocated_ip)
                            encoded_message = base64.b64encode(message.encode()).decode()
                            queue.send("devops", encoded_message)
                            devops_run = True
    if devops_run and devops_url != "":
        print("[INF] Triggering DevOps Webhook")
        requests.post(devops_url, data="{}", headers={"Content-Type": "application/json"})
    

main()