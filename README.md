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

[Code examples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/servicebus/azure-servicebus/samples)

[KEDA trigger for Service Bus](https://keda.sh/docs/2.14/scalers/azure-service-bus/)

https://tinydb.readthedocs.io/en/latest/getting-started.html#basic-usage

https://learn.microsoft.com/en-us/azure/container-apps/jobs?tabs=azure-cli#scheduled-jobs