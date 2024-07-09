import os  
import datetime  
from azure.mgmt.appcontainers import ContainerAppsAPIClient  
from azure.servicebus import ServiceBusMessage, ServiceBusClient
from azure.identity import DefaultAzureCredential  
from time import sleep  
  
class SBClient:
    def __init__(self, fully_qualified_namespace, queue_name, credential):
        print("[INF] Initializing Service Bus client")
        self.default_queue = queue_name
        self.servicebus_client = ServiceBusClient(fully_qualified_namespace, credential)

    def send_message(self, message, queue_name=None):
        print("[INF] Sending a message/-s")
        queue_name = queue_name or self.default_queue
        sender = self.servicebus_client.get_queue_sender(queue_name)
        with sender:
            if isinstance(message, str):
                sender.send_messages([ServiceBusMessage(message)])
            elif isinstance(message, list):
                for item in message:
                    sender.send_messages([ServiceBusMessage(item)])
            else:
                raise ValueError("[ERR] Invalid message type. Message must be a string or a list.")
            
    def receive_message(self, peek = False, queue_name=None):
        print("[INF] Receiving a message/-s")
        queue_name = queue_name or self.default_queue
        with self.servicebus_client.get_queue_receiver(queue_name) as receiver:
            messages = receiver.receive_messages(max_message_count=1)
            if peek:
                for msg in messages:
                    receiver.peek_message(msg)
            return messages
  
def trigger_container_app_job(resource_id,credential):  
    app_sub, app_group, app_name = resource_id.split('/')[2], resource_id.split('/')[4], resource_id.split('/')[-1]  
    print(resource_id.split('/'))  
  
    container_client = ContainerAppsAPIClient(credential, app_sub)  
  
    print(container_client.jobs.begin_start(  
        resource_group_name=app_group,  
        job_name=app_name,  
    ).result())

  
def main():  
    service_bus_namespace = os.environ.get("SERVICE_BUS_NAMESPACE")  
    queue_name = os.environ.get("SERVICE_BUS_QUEUE_NAME")  
    container_app_job_resource_id = os.environ.get("CONTAINER_APP_JOB_RESOURCE_ID")

    if not service_bus_namespace or not queue_name or not container_app_job_resource_id:
        print("[ERR] Missing environment variables")
        return

    credential = DefaultAzureCredential()
    
    sb_client = SBClient(service_bus_namespace, queue_name, credential)

    start_time = datetime.datetime.now()  
    end_time = start_time + datetime.timedelta(minutes=10)  # run for 10 minutes  
   
    while datetime.datetime.now() < end_time:    
        messages = sb_client.receive_message(peek=True)  
        if messages:    
            print("[INF] New message recieved")  
            print(messages.body)  
            trigger_container_app_job(container_app_job_resource_id, credential)    
            return    
        sleep(60)  # Wait for 1 minute    

main()