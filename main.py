import os    
import datetime    
from azure.mgmt.appcontainers import ContainerAppsAPIClient    
from azure.servicebus import ServiceBusMessage, ServiceBusClient, ServiceBusReceivedMessage
from azure.identity import DefaultAzureCredential    
from azure.mgmt.resource import ResourceManagementClient
from time import sleep    
import json

class AzClient:
    def __init__(self, subscription_id, credential):
        print("[INF] Initializing Template Deployer")
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
        if api_ver is None:
            api_ver = self.get_provider_latest_api_version(resource_id.split('/')[6], resource_id.split('/')[7])
        try:
            response = self.resource_client.resources.get_by_id(resource_id, api_version=api_ver)
        except Exception as e:
            print("[ERR]" + str(e))
            response = ""
        return response

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


class SBClient:  
    def __init__(self, fully_qualified_namespace, queue_name, credential):  
        print("[INF] Initializing Service Bus client")  
        self.collected_events = []
        self.default_queue = queue_name  
        self.servicebus_client = ServiceBusClient(fully_qualified_namespace, credential)  
  
    def send_message(self, message, queue_name=None):  
        print("[INF] Sending a message/-s")  
        queue_name = queue_name or self.default_queue  
        sender = self.servicebus_client.get_queue_sender(queue_name)  
        with sender:  
            sender.send_messages(message)  
              
    def receive_message(self, peek = False, queue_name=None, max_message_count=100):  
        print("[INF] Receiving a message/-s")  
        queue_name = queue_name or self.default_queue  
        with self.servicebus_client.get_queue_receiver(queue_name) as receiver:  
            messages = receiver.receive_messages(max_message_count=max_message_count)  
            for message in messages:  
                if peek:  
                    receiver.complete_message(message)  
                return messages  
            
    def genereate_message(self, msg: ServiceBusReceivedMessage, az_client: AzClient):  
        print("[INF] Parse event and generate a message")
        parsed = json.loads(str(msg).lower())
        original_subject =  parsed['subject']
        az_client.set_subscription(parse_resource_id(original_subject)[0])
        match parsed['data']['authorization']['action']:
            case "microsoft.network/virtualnetworks/virtualnetworkpeerings/write":
                subject = "vnet-peering"
                arm_result = az_client.get_resource_by_id(original_subject,"2024-01-01")
                if arm_result != "":
                    subject = "vnet-peering"
                    body = json.dumps({"peeringState": arm_result.properties["provisioningState"],"peeringSyncLevel": arm_result.properties["peeringSyncLevel"],"remoteVirtualNetworkId": arm_result.properties["remoteVirtualNetwork"]["id"],"remoteAddressSpace":arm_result.properties["remoteAddressSpace"]["addressPrefixes"]})
                else:
                    subject = "failed"
                    body = parsed
        self.collected_events.append(ServiceBusMessage(body=body, subject=subject, content_type="application/json"))
    
    def total_events_number(self):
        return len(self.collected_events)

    def send_events(self):
        print("[INF] Sending collected events")
        for event in self.collected_events:
            self.send_message(event,queue_name=event.subject)
        self.collected_events = []
  
def parse_resource_id(resource_id):
    return resource_id.split('/')[2], resource_id.split('/')[4],resource_id.split('/')[6], resource_id.split('/')[8]

def trigger_container_app_job(resource_id,credential):
    print("[INF] Triggering container app job")
    app_sub, app_group, app_name = resource_id.split('/')[2], resource_id.split('/')[4], resource_id.split('/')[-1]    
    
    container_client = ContainerAppsAPIClient(credential, app_sub)    
    
    print("[INF] App job run result: " + container_client.jobs.begin_start(    
        resource_group_name=app_group,    
        job_name=app_name,    
    ).status())  
    
def manager():    
    container_app_job_resource_id = os.environ.get("CONTAINER_APP_JOB_RESOURCE_ID")  
    
    if not service_bus_namespace or not queue_name or not container_app_job_resource_id:  
        print("[ERR] Missing environment variables")  
        return  

    default_subscription = parse_resource_id(container_app_job_resource_id)[0]
  
    credential = DefaultAzureCredential()  
      
    sb_client = SBClient(service_bus_namespace, queue_name, credential)  
    az_client = AzClient(default_subscription, credential)

    start_time = datetime.datetime.now()    
    end_time = start_time + datetime.timedelta(minutes=3) 
     
    while datetime.datetime.now() < end_time:      
        messages = sb_client.receive_message(peek = False)    
        if messages:
            for message in messages:
                sb_client.genereate_message(message, az_client)
            print("[INF] Total events: " + str(sb_client.total_events_number()))
            sb_client.send_events()
            trigger_container_app_job(container_app_job_resource_id, credential)
            return
        sleep(30) 

def runner():
    service_bus_namespace = os.environ.get("SERVICE_BUS_NAMESPACE")    
    queue_name = os.environ.get("SERVICE_BUS_QUEUE_NAME")


job_role = os.environ.get("JOB_ROLE").tolower()
service_bus_namespace = os.environ.get("SERVICE_BUS_NAMESPACE")    
queue_name = os.environ.get("SERVICE_BUS_QUEUE_NAME") 
print("[INF] Running as " + job_role)

match job_role:
    case "manager":
        manager()
    case "runner":
        runner()


