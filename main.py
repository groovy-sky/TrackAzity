import os    
import datetime    
from azure.mgmt.appcontainers import ContainerAppsAPIClient    
from azure.servicebus import ServiceBusMessage, ServiceBusClient, ServiceBusReceivedMessage
from azure.identity import DefaultAzureCredential    
from time import sleep    
import json
import hashlib

class SBClient:  
    def __init__(self, fully_qualified_namespace, queue_name, credential):  
        print("[INF] Initializing Service Bus client")  
        self.collected_events = []
        self.default_queue = queue_name  
        self.servicebus_client = ServiceBusClient(fully_qualified_namespace, credential)  
  
    async def send_message(self, message, queue_name=None):  
        print("[INF] Sending a message/-s")  
        queue_name = queue_name or self.default_queue  
        sender = self.servicebus_client.get_queue_sender(queue_name)  
        with sender:  
            if isinstance(message, str):  
                sender.send_messages(self.genereate_message(message))  
            elif isinstance(message, list):  
                for item in message:  
                    self.send_message(item, queue_name)
            else:  
                raise ValueError("[ERR] Invalid message type. Message must be a string or a list.")  
              
    def receive_message(self, peek = False, queue_name=None, max_message_count=100):  
        print("[INF] Receiving a message/-s")  
        queue_name = queue_name or self.default_queue  
        with self.servicebus_client.get_queue_receiver(queue_name) as receiver:  
            messages = receiver.receive_messages(max_message_count=max_message_count)  
            for message in messages:  
                if peek:  
                    receiver.complete_message(message)  
                return messages  
            
    def genereate_message(self, body, subject=None, content_type="application/json"):  
        if content_type == "application/json":
            message = json.dumps({"body": body})
        else:
            message = body
        return ServiceBusMessage(message, subject=subject, content_type=content_type)
    
    def store_event(self, event):
        self.collected_events.append({hashlib.md5(event["subject"].lower().encode()).hexdigest(): event})

    def return_events(self):
        return self.collected_events
  
def trigger_container_app_job(resource_id,credential):
    print("[INF] Triggering container app job")
    app_sub, app_group, app_name = resource_id.split('/')[2], resource_id.split('/')[4], resource_id.split('/')[-1]    
    
    container_client = ContainerAppsAPIClient(credential, app_sub)    
    
    print("[INF] App job run result: " + container_client.jobs.begin_start(    
        resource_group_name=app_group,    
        job_name=app_name,    
    ).status())  

def parse_message(msg: ServiceBusReceivedMessage):
    print("[INF] Parsing message")
    parsed = json.loads(str(msg))
    result = {'subject': parsed['subject'],'eventType':parsed['eventType'],'action': parsed['data']['authorization']['action']}
    return result
    
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
    end_time = start_time + datetime.timedelta(minutes=3) 
     
    while datetime.datetime.now() < end_time:      
        messages = sb_client.receive_message(peek = False)    
        if messages:
            for message in messages:
                sb_client.store_event(parse_message(message))

            print(sb_client.return_events())
            trigger_container_app_job(container_app_job_resource_id, credential)
            return
        sleep(30) 
  
main()  

