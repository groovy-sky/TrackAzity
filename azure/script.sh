#/bin/bash

storage_location="SwedenCentral"
storage_rg="trackazity-storage-rg"

# Create a resource group
az group create --name $storage_rg --location $storage_location

# Deploy ARM template for storage account and related environemnt
arm_storage=$(az deployment group create --resource-group $storage_rg --template-file Storage.json | jq -r '. | .properties | .outputs')

topic_name=$(echo $arm_storage | jq -r '.topicName.value')
storage_account_name=$(echo $arm_storage | jq -r '.storageAccountName.value')

container_location="WestEurope"
container_name="trackazity-container-rg"
hub_vnet_id="/subscriptions/20f105d9-0e32-43bb-bd88-3f616a393940/resourceGroups/DvL08g2ULxDxn6/providers/Microsoft.Network/virtualNetworks/vnet-lwxlt98lt28id9"
devops_org="3ap9lq"
devops_webhook="vnet-connection"

# Create a resource group
az group create --name $container_name --location $container_location

# Deploy ARM template for container and related environemnt
az deployment group create --resource-group $container_name --template-file Container.json --parameters storageName=$storage_account_name 