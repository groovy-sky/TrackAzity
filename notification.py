from azure.communication.email import EmailClient
from azure.identity import DefaultAzureCredential

endpoint = "https://6d6a8ddd-efcc-47c5-a71c-6550b1baddf3.azurecomm.net"
sender_address = "DoNotReply@6d6a8ddd-efcc-47c5-a71c-6550b1baddf3.azurecomm.net"
recipient_address = "3ap9.lq@gmail.com"

POLLER_WAIT_TIME = 10

message = {
    "senderAddress": sender_address,
    "recipients":  {
        "to": [{"address": recipient_address}],
    },
    "content": {
        "subject": "Test email from Python Sample",
        "plainText": "This is plaintext body of test email.",
        "html": "<html><h1>This is the html body of test email.</h1></html>",
    }
}

try:
    client = EmailClient(endpoint, DefaultAzureCredential())

    poller = client.begin_send(message);

    time_elapsed = 0
    while not poller.done():
        print("Email send poller status: " + poller.status())

        poller.wait(POLLER_WAIT_TIME)
        time_elapsed += POLLER_WAIT_TIME

        if time_elapsed > 18 * POLLER_WAIT_TIME:
            raise RuntimeError("Polling timed out.")

    if poller.result()["status"] == "Succeeded":
        print(f"Successfully sent the email (operation id: {poller.result()['id']})")
    else:
        raise RuntimeError(str(poller.result()["error"]))
    
except Exception as ex:
    print(ex)