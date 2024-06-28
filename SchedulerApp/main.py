import os  
import datetime  
from azure.mgmt.appcontainers import ContainerAppsAPIClient  
from azure.servicebus import ServiceBusClient
from azure.identity import DefaultAzureCredential  
from time import sleep  
  
credential = DefaultAzureCredential()  
  
def trigger_container_app_job(resource_id):  
    app_sub, app_group, app_name = resource_id.split('/')[2], resource_id.split('/')[4], resource_id.split('/')[-1]  
    print(resource_id.split('/'))  
  
    container_client = ContainerAppsAPIClient(credential, app_sub)  
  
    print(container_client.jobs.begin_start(  
        resource_group_name=app_group,  
        job_name=app_name,  
    ).result())
  
def check_service_bus():  
    service_bus_namespace = os.environ.get("SERVICE_BUS_NAMESPACE")  
    queue_name = os.environ.get("SERVICE_BUS_QUEUE_NAME")  
    container_app_job_resource_id = os.environ.get("CONTAINER_APP_JOB_RESOURCE_ID")  
  
    service_bus_client = ServiceBusClient(service_bus_namespace, credential)  
    queue_receiver = service_bus_client.get_queue_receiver(queue_name)  
  
    start_time = datetime.datetime.now()  
    end_time = start_time + datetime.timedelta(minutes=10)  # run for 10 minutes  
  
    with queue_receiver:  
        while datetime.datetime.now() < end_time:  
            peeked_msgs = queue_receiver.peek_messages(max_message_count=1)  
            if peeked_msgs:  
                print("[INF] New message recieved")  
                trigger_container_app_job(container_app_job_resource_id)  
                return  
            sleep(60)  # Wait for 1 minute  
  
  
def main():  
    check_service_bus()  
  
if __name__ == '__main__':  
    main()  
