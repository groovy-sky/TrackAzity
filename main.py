from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueServiceClient,BinaryBase64DecodePolicy
from azure.mgmt.resource import ResourceManagementClient
import os
import base64
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



class QueueClient:
    def __init__(self, url, credential):
        self.client = QueueServiceClient(account_url=url, credential=credential,  message_decode_policy=BinaryBase64DecodePolicy())

    def receive(self, queue_name, recieve_only = False):
        response = []
        queue = self.client.get_queue_client(queue_name)
        for message in queue.receive_messages():
            response.append(base64.b64decode(message.content))
            if recieve_only:
                queue.delete_message(message)
        return response

    def send(self, queue_name, message):
        queue_client = self.client.get_queue_client(queue_name)
        queue_client.send_message(message)

def main():
    storage_name = os.environ.get("STORAGE_NAME")
    queue_name = os.environ.get("QUEUE_NAME") 
    queue_url = "https://" + storage_name + ".queue.core.windows.net"
    cred = DefaultAzureCredential()
    queue = QueueClient(queue_url, cred)
    default_subscription = "00000000-0000-0000-0000-000000000000"
    az_client = AzClient(default_subscription, cred)
    for item in queue.receive(queue_name):
        peering_info, fail = az_client.get_resource_by_id(json.loads(item).get("subject"),"2024-01-01")
        if peering_info != "" and not fail:  
            print(peering_info)

main()