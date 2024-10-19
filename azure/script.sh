#/bin/bash

storage_location="SwedenCentral"
storage_rg="trackazity-storage-rg"

# Create a resource group
az group create --name $storage_rg --location $storage_location

# Deploy ARM template for storage account and related environemnt
arm_storage=$(az deployment group create --resource-group $storage_rg --template-file Storage.json | jq -r '. | .properties | .outputs')

topic_name=$(echo $arm_storage | jq -r '.topicName.value')
storage_account_name=$(echo $arm_storage | jq -r '.storageAccountName.value')