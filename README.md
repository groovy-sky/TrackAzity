# az-arm-py

1. Init IP table (from file or Hub VNet)
2. Allocate IP range

Microsoft.Network/virtualNetworks/virtualNetworkPeerings/write
Microsoft.Network/virtualNetworks/peer/action

Microsoft.Resources.ResourceWriteSuccess

[Trigger Job by Service Bus]https://techcommunity.microsoft.com/t5/apps-on-azure-blog/deploying-an-event-driven-job-with-azure-container-app-job-and/ba-p/3909279

https://github.com/Azure-Samples/container-apps-jobs

https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-python-how-to-use-queues?tabs=passwordless

https://learn.microsoft.com/en-us/azure/devops/service-hooks/services/webhooks?view=azure-devops


[Code examples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/servicebus/azure-servicebus/samples)

[KEDA trigger for Service Bus](https://keda.sh/docs/2.14/scalers/azure-service-bus/)

[TinyDB library](https://tinydb.readthedocs.io/en/latest/getting-started.html#basic-usage)

[Deploy ARM template in Python](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/deploy-python)

https://learn.microsoft.com/en-us/azure/container-apps/jobs?tabs=azure-cli#scheduled-jobs

https://github.com/Azure/azure-sdk-for-go/blob/sdk/resourcemanager/appcontainers/armappcontainers/v2.1.0/sdk/resourcemanager/resources/armresources/client.go

https://learn.microsoft.com/en-us/rest/api/containerapps/jobs/start?view=rest-containerapps-2024-03-01&tabs=HTTP

[Managed ID for Ansible](https://techcommunity.microsoft.com/t5/core-infrastructure-and-security/configure-ansible-to-use-a-managed-identity-with-azure-dynamic/ba-p/1062449)

```
from azure.servicebus import ServiceBusClient, ServiceBusMessage  
import time  
  
connection_str = 'your_connection_string'  
queue_name = 'your_queue_name'  
cidr_size = '/24'  # replace this with your actual CIDR size  
  
service_bus_client = ServiceBusClient.from_connection_string(connection_str)  
  
with service_bus_client:  
    sender = service_bus_client.get_queue_sender(queue_name)  
    with sender:  
        epoch_time = int(time.time())  
        cidr_int = int(cidr_size[1:])  # get the integer value after the slash  
        message_id = str(cidr_int ^ epoch_time)  # XOR operation  
          
        message = ServiceBusMessage(cidr_size, message_id=message_id)  
        sender.send_messages(message)  
        print(f"Sent a single message with ID: {message_id}")  

```


```
export RESOURCE_GROUP="hub-vnet"
export JOB_NAME="$RESOURCE_GROUP-app-job"
export ENVIRONMENT="$RESOURCE_GROUP-env"
export QUEUE="send-test"
export NAMESPACE="vnetbus"
export CONTAINER_IMAGE_NAME="gr00vysky/url-query:latest"
export URL="https://webhook.site/fdb92cd0-7aeb-46f6-9950-7a7b001ba3e8"
export LOCATION="westeurope"

az containerapp env create \
    --name "$ENVIRONMENT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION"

az containerapp job create --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" --environment "$ENVIRONMENT" --trigger-type "Event" --replica-timeout "1800" --replica-retry-limit "1" --replica-completion-count "1" --parallelism "1" --min-executions "0" --max-executions "1" --polling-interval "60" --scale-rule-name "queue" --scale-rule-type "azure-servicebus" --scale-rule-metadata "queueName=$QUEUE" "namespace=$NAMESPACE" "messageCount=1" "connectionFromEnv=CONN_STR" --image "docker.io/$CONTAINER_IMAGE_NAME" --cpu "0.5" --memory "1Gi" --env-vars "URL=$URL" "CONN_STR=Endpoint=sb://vnetbus.servicebus.windows.net/;SharedAccessKeyName=reader;SharedAccessKey=iA4WA3jhTD9G7b2q4HNy0UCP8WlDC8sCT+ASbJreYMA=;EntityPath=send-test" --mi-system-assigned


az containerapp job start -n "$JOB_NAME" -g "$RESOURCE_GROUP"

az containerapp job create \
    --name "$JOB_NAME"\
    --resource-group "$RESOURCE_GROUP"\
    --environment "$ENVIRONMENT"\
    --trigger-type "Event"\
    --replica-timeout "1800"\
    --replica-retry-limit "1"\
    --replica-completion-count "1"\
    --parallelism "1"\
    --min-executions "0"\
    --max-executions "10"\
    --polling-interval "60"\
    --scale-rule-name "queue"\
    --scale-rule-type "azure-servicebus"\
    --scale-rule-metadata "queueName=xxxxx" "namespace=xxxxxx" "messageCount=1"\
    --scale-rule-auth "connection=connection-string-secret"\
    --image "$CONTAINER_REGISTRY_NAME.azurecr.io/$CONTAINER_IMAGE_NAME"\
    --cpu "0.5"\
    --memory "1Gi"\
    --secrets "connection-string-secret=$QUEUE_CONNECTION_STRING"\
    --registry-server "$CONTAINER_REGISTRY_NAME.azurecr.io"\
    --env-vars "AZURE_STORAGE_QUEUE_NAME=$QUEUE_NAME" "AZURE_SERVICE_BUS_CONNECTION_STRING=secretref:connection

```

```

credential = DefaultAzureCredential()

spoke_sub_id = os.environ["AZURE_SUBSCRIPTION_ID"]
spoke_res_grp = "exampleGroup"
spoke_ip = "192.168.150.0/24"
spoke_vnet_name = "exampleVnet4"
spoke_resource_id = "/subscriptions/" + spoke_sub_id + "/resourceGroups/" + spoke_res_grp + "/providers/Microsoft.Network/virtualNetworks/" + spoke_vnet_name

spoke = TemplateDeployer(spoke_sub_id, credential)


print(spoke.deploy_template(spoke_res_grp, "vnet_init.json", {"vnetAddressPrefix": {"value": spoke_ip},"vnetName": {"value": spoke_vnet_name},"createSubnet":{"value":True}}))

hub_res_id = os.environ["HUB_VNET_ID"]

spoke.deploy_template(spoke_res_grp, "vnet_peering.json", {"vnetName": {"value": spoke_vnet_name},"remoteVnetId": {"value": hub_res_id},"peeringName":{ "value": "hubToSpoke"}})
```