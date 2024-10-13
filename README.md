# TrackAzity

![](TrackAzity.svg)

## Introduction

TrackAzity is a simple and easy-to-use tool for managing IPv4 address assignments and tracking. It is specifically designed for use with Azure Virtual Networks (VNets). With TrackAzity, you can allocate IP ranges for new or existing Azure VNets and generate IP usage reports for your Hub VNet. All IP allocation changes are stored in an Azure Storage Table, and the IP usage report is presented as a Markdown table in an Azure DevOps repository.

TrackAzity simplifies the process of managing IP address assignments within your Azure network infrastructure. By using this tool, you can easily allocate IP ranges, track IP usage, and generate reports to ensure efficient utilization of IP resources.

### Key Components

Azure Resource Group:
* Azure Storage Account: Used for messaging (using Queue) and IP reservation state (using Table).
* Azure Container App: The core solution responsible for IP allocation.
* Event Grid System Topic: Detects IP-related events and forwards them to the Container App.
* Template Spec: Provides user input for required VNet changes.

Azure DevOps Repository:
* Main Pipeline: Handles VNet change runs.
* Report Pipeline: Deploys the Spoke VNet usage report.


1. Init IP table (from file or Hub VNet)
2. Allocate IP range

## To-Do
- [x] Report functionality
- [ ] Backup storage allocation to repository
- [ ] E-mail integrity ?
- [ ] Expand VNet template
- [ ] Delete Spoke IP allocation functionality


A tag value can have a maximum of 256 characters.


**DvL08g2ULxDxn6**
* vnet-lwxlt98lt28id9
* event-topic-lgddktlx6c0eol




STRG
strg4whurqk7qms9x4


0. Deploy ARM
1. Assign to Event Topic Storage Queue Sender role
2. Assign to App Job Queue Reciever role
3. Configure Event triggering

[Azure DevOps code wiki as a code](https://learn.microsoft.com/en-us/azure/devops/project/wiki/provisioned-vs-published-wiki?view=azure-devops)

[Commit to repository from pipeline itself](https://programmingwithwolfgang.com/create-git-commits-in-azure-devops-yaml-pipeline/)

[DevOps identity](https://blog.xmi.fr/posts/azure-devops-authenticate-as-managed-identity/)

https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/azure-cli-v2?view=azure-pipelines

[How to send an email using Azure Communication Services](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/communication-services/quickstarts/email/send-email.md)

https://github.com/Azure-Samples/communication-services-python-quickstarts/tree/main/use-managed-Identity

[Azure DevOps service hooks integration](https://learn.microsoft.com/en-us/azure/devops/service-hooks/overview?view=azure-devops)

[Trigger Job by Service Bus](https://techcommunity.microsoft.com/t5/apps-on-azure-blog/deploying-an-event-driven-job-with-azure-container-app-job-and/ba-p/3909279)

https://github.com/Azure-Samples/container-apps-jobs

https://learn.microsoft.com/en-us/azure/devops/service-hooks/services/webhooks?view=azure-devops

[Table Python client](https://pypi.org/project/azure-data-tables/)

[Table examples](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/tables/azure-data-tables/samples/sample_insert_delete_entities.py#L67-L73)

[Code examples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/servicebus/azure-servicebus/samples)

[KEDA trigger for Service Bus](https://keda.sh/docs/2.14/scalers/azure-service-bus/)

[TinyDB library](https://tinydb.readthedocs.io/en/latest/getting-started.html#basic-usage)

[Deploy ARM template in Python](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/deploy-python)

[Azure Python SDK samples](https://github.com/Azure-Samples/azure-samples-python-management/tree/main/samples/resources)

[ResourcesOperations Class Methods](https://learn.microsoft.com/en-us/python/api/azure-mgmt-resource/azure.mgmt.resource.resources.v2021_04_01.operations.resourcesoperations?view=azure-python)

[Azure Tables client library for Python](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/tables/azure-data-tables)

https://learn.microsoft.com/en-us/azure/container-apps/jobs?tabs=azure-cli#scheduled-jobs

https://github.com/Azure/azure-sdk-for-go/blob/sdk/resourcemanager/appcontainers/armappcontainers/v2.1.0/sdk/resourcemanager/resources/armresources/client.go

https://learn.microsoft.com/en-us/rest/api/containerapps/jobs/start?view=rest-containerapps-2024-03-01&tabs=HTTP
