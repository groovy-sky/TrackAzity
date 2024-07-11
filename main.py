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
  
    async def send_message(self, message, queue_name=None, content_type="application/json"):  
        print("[INF] Sending a message/-s")  
        queue_name = queue_name or self.default_queue  
        sender = self.servicebus_client.get_queue_sender(queue_name)  
        with sender:  
            if isinstance(message, str):  
                sender.send_messages([ServiceBusMessage(message,content_type=content_type)])  
            elif isinstance(message, list):  
                for item in message:  
                    self.send_message(item, queue_name, content_type)
            else:  
                raise ValueError("[ERR] Invalid message type. Message must be a string or a list.")  
              
    def receive_message(self, peek = False, queue_name=None, max_message_count=1):  
        print("[INF] Receiving a message/-s")  
        queue_name = queue_name or self.default_queue  
        with self.servicebus_client.get_queue_receiver(queue_name) as receiver:  
            messages = receiver.receive_messages(max_message_count=max_message_count)  
            for message in messages:  
                if peek:  
                    receiver.complete_message(message)  
                return messages  
  
def trigger_container_app_job(resource_id,credential):
    print("[INF] Triggering container app job")
    app_sub, app_group, app_name = resource_id.split('/')[2], resource_id.split('/')[4], resource_id.split('/')[-1]    
    
    container_client = ContainerAppsAPIClient(credential, app_sub)    
    
    print("[INF] App job run result: " + container_client.jobs.begin_start(    
        resource_group_name=app_group,    
        job_name=app_name,    
    ).status())  
  
    
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
    end_time = start_time + datetime.timedelta(minutes=3)  # run for 10 minutes    
     
    while datetime.datetime.now() < end_time:      
        message = sb_client.receive_message(peek = False)    
        if message:
            print("[INF] New message in Service Bus has been detected")    
            trigger_container_app_job(container_app_job_resource_id, credential)
            return      
        sleep(30)  # Wait for 1 minute      
  
main()  
