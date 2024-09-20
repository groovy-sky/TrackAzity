from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueServiceClient,BinaryBase64DecodePolicy
from azure.data.tables import TableServiceClient,UpdateMode
from azure.mgmt.resource import ResourceManagementClient
from datetime import datetime, timezone  
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
    def reserve_ip_entity(self, ip_size, vnet_id, location, latest_event, additional_data = ""):
        print("[INF] Reserving IP entity for " + vnet_id)
        vnet_subscription = vnet_id.split('/')[2]
        vnet_name = vnet_id.split('/')[8]
        cidr = self.allocate_ip(ip_size)
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
    def allocate_ip(self, requested_size):
        print("[INF] Allocating IP entity")  
        query_size = requested_size  
        allocated_ip = None  
        while query_size > 1 and not allocated_ip:  
            print("[INF] Searching for IP with size: " + str(query_size))  
            result = self.query("Used eq false and AddressCount eq {size}".format(size=ip_mask[query_size]))  
            try:  
                next_result = next(result)  
                if query_size == requested_size:  
                    allocated_ip = next_result["IP"]  
                else:  
                    # Split the IP range to requested size and update the table.   
                    # Should mark original IP as disabled, create new IPs with the split range   
                    # and store their parent key into ChildKeys  
                    cidr = next_result["IP"]  
                    network = ipaddress.ip_network(cidr, strict=False)  
                    child_keys = []  
                    for ip in network.subnets(new_prefix=requested_size):  
                        ip = str(ip)  
                        self.create_ip_entity(ip, "", "", "", "", "", "", "", "", "")  
                        child_keys.append(cidr_to_int(ip))  
                        allocated_ip = ip  
                    self.upsert({"PartitionKey": cidr_to_int(cidr),   
                                 "RowKey": hashlib.md5(cidr_to_int(cidr).encode()).hexdigest(),   
                                 "ChildKeys": ",".join(child_keys),   
                                 "Used": True})  
            except StopIteration:  
                next_result = []  
            query_size -= 1  
        return allocated_ip  
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

    def receive(self, queue_name, read_only=False, event=False):
        print("[INF] Receiving messages from queue")
        response = []
        queue = self.client.get_queue_client(queue_name)
        for message in queue.receive_messages():
            decoded_message = base64.b64decode(message.content)
            if event:
                decoded_message = self.parse_event(decoded_message)
            response.append(decoded_message)
            if not read_only:
                queue.delete_message(message)
        return response

    def parse_event(self, json_string):  
        print("[INF] Parsing Event")  
        json_data = json.loads(json_string)  
        date_string = json_data['eventTime']
        date_string = date_string[:26] + "Z"  # Truncate to microseconds  

        dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")  
        dt = dt.replace(tzinfo=timezone.utc)  # Replace naive datetime object with a timezone-aware one  
        epoch_time = int(dt.timestamp())  

        result = {  
            'subject': json_data['subject'].lower(),  
            'eventType': json_data['eventType'].lower(),  
            'operationName': json_data['data']['operationName'].lower(),  
            'eventTime': epoch_time
        }  
        return result 

    def send(self, queue_name, message, encode=True):
        print("[INF] Sending message to queue")
        if encode:
            message = base64.b64encode(message.encode()).decode()
        queue_client = self.client.get_queue_client(queue_name)
        queue_client.send_message(message)

    def store_error(self, error, queue_name="errors"):
        print("[INF] Storing error message")
        queue_client = self.client.get_queue_client(queue_name)
        queue_client.send_message(error)

def main():
    storage_name = os.environ.get("STORAGE_NAME")
    default_subscription = os.environ.get("DEFAULT_SUBSCRIPTION", "00000000-0000-0000-0000-000000000000")
    hub_id = os.environ.get("HUB_ID","")
    devops_org = os.environ.get("DEVOPS_ORG","")
    devops_webhook = os.environ.get("DEVOPS_WEBHOOK","")
    devops_run = False

    if devops_org != "" and devops_webhook != "":
        devops_url = "https://dev.azure.com/{organization}/_apis/public/distributedtask/webhooks/{webhook}?api-version=6.0-preview".format(organization=devops_org, webhook=devops_webhook)
    
    cred = DefaultAzureCredential()

    ips_table = TableClient(storage_name, os.environ.get("TABLE_NAME", "ips"), cred)
    az_client = AzClient(default_subscription, cred)

    if hub_id == "":
        print("[ERR] Hub ID not found")
        return
    else:
        hub_name = hub_id.split('/')[8]
        hub_rg = hub_id.split('/')[4]
        hub_sub = hub_id.split('/')[2]

    job_role = os.environ.get("JOB_ROLE").lower()
    job_queue = {"system":"system","azure":"azure"}[job_role]
    queue = QueueClient(storage_name, cred)

    # Counter for number of message send to DevOps (maximum 32 messages allowed)
    devops_counter = 0

    if os.environ.get("SPOKE_IP_RANGES") != "":
            spoke_ips = os.environ.get("SPOKE_IP_RANGES","")
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
                _, exists = ips_table.get_ip_entity(ip)
                if not exists:
                    ips_table.create_ip_entity(ip, "", "", "", "", "", "", "", "","")
            # Get all peerings from the hub
            peerings_list, ok = az_client.get_resource_by_id(hub_id+"/virtualNetworkPeerings","2024-01-01")
            if ok:
                devops_run = True
                for peer in peerings_list.additional_properties["value"]:
                    remote_vnet_id = peer["properties"]["remoteVirtualNetwork"]["id"]
                    message = "az rest --method get --url https://management.azure.com"+ remote_vnet_id +"?api-version=2024-01-01 > ../peerings/" + remote_vnet_id.split("/")[-1] + ".json"
                    devops_counter += 1
                    queue.send("devops", message)

    for item in queue.receive(job_queue, read_only = True, event = True):
        # Process the event based on the operation name
        match item["operationName"]:
            # Process new VNet allocation request
            case "microsoft.resources/deployments/write":
                deployment_info, ok = az_client.get_resource_by_id(item["subject"], "2021-04-01")
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
                    queue.store_error(item)
                    return
                # Check for duplicates
                vnet_ips = 0
                try:
                    for ip in ips_table.query("VNetName eq '{vnet}' and AdditionalData eq {date}".format(vnet=vnet_name, date=event_time)):
                        vnet_ips += 1
                except Exception:
                    pass
                # Allocate IP if no duplicate found
                if vnet_ips == 0:
                    allocated_ip = ips_table.allocate_ip(vnet_size)
                    reserved_ip = ips_table.reserve_ip_entity(allocated_ip, vnet_id, vnet_location, item["eventType"], event_time)
                    message = "az account set -s {subscription};\naz network vnet create -g {rg} -n {vnet} --address-prefix {ip} --subnet-name default --subnet-prefixes {ip};\naz network vnet peering create --name {hub_name} --remote-vnet {hub_id} --resource-group {rg} --vnet-name {vnet};\naz account set -s {hub_sub};\naz network vnet peering create --name {vnet} --remote-vnet /subscriptions/{subscription}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet} --resource-group {hub_rg} --vnet-name {hub_name}".format(subscription=subscription_id, rg=vnet_rg, vnet=vnet_name,ip = reserved_ip, hub_name=hub_name, hub_id=hub_id, hub_sub=hub_sub, hub_rg=hub_rg)
            # Process VNet peering request
            case "microsoft.network/virtualnetworks/virtualnetworkpeerings/write":
                peering_info, ok = az_client.get_resource_by_id(item["subject"],"2024-01-01")
                if peering_info != "" and ok:  
                    remote_vnet_id = peering_info.properties["remoteVirtualNetwork"]["id"]
                    message = "az rest --method get --url https://management.azure.com"+ remote_vnet_id +"?api-version=2024-01-01 > ../peerings/" + peering_info["name"] + ".json"
                else:
                    print("[ERR] Peering info not found")
                    queue.store_error(item)
                    return
        devops_counter += 1
        queue.send("devops", message)
    requests.post(devops_url, data="{}", headers={"Content-Type": "application/json"})
    if devops_run and devops_url != "":
        print("[INF] Triggering DevOps Webhook")
        for _ in range(round(devops_counter/30)+1):
            requests.post(devops_url, data="{}", headers={"Content-Type": "application/json"})
    

main()