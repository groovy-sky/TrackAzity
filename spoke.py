import os
import json
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode

class TemplateDeployer:
    def __init__(self, subscription_id, credential):
        self.credential = credential
        self.subscription_id = subscription_id
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)

    def deploy_template(self, resource_group, deployment_name, template_file, parameters):
        with open(template_file, "r") as file:
            template_body = json.load(file)

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

        return deployment_result


credential = DefaultAzureCredential()

subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

deployer = TemplateDeployer(subscription_id, credential)
deployer.deploy_template("exampleGroup", "exampleDeployment", "spoke.json", {"vnetAddressPrefix": {"value": ["10.16.16.0/24"]},"vnetName": {"value": "exampleVnet"}})