import os
from azure.servicebus import ServiceBusMessage, ServiceBusClient
from azure.identity import DefaultAzureCredential

class SBClient:
    def __init__(self, fully_qualified_namespace, queue_name, credential=DefaultAzureCredential()):
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
            
    def receive_message(self, queue_name=None, wait_time=30):
        print("[INF] Receiving a message/-s")
        queue_name = queue_name or self.default_queue
        with self.servicebus_client.get_queue_receiver(queue_name,  max_wait_time=wait_time) as receiver:
            for msg in receiver:
                print(str(msg))
                receiver.complete_message(msg)

fully_qualified_namespace = os.environ['SERVICEBUS_FULLY_QUALIFIED_NAMESPACE']
queue_name = os.environ["SERVICEBUS_QUEUE_NAME"]

sb = SBClient(fully_qualified_namespace, queue_name)
sb.send_message('Msg')
#sb.receive_message()
