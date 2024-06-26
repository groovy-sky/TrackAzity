package main

import (
	"context"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/resources/armresources"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/arm"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/runtime"
	"log"
	"os"
	"fmt"
	"strings"
	"net/http"
)

var (
	resourceGroupClient *armresources.ResourceGroupsClient
	resourcesClient     *armresources.Client
)

type JobsClient struct {
	internal       *arm.Client
	subscriptionID string
}	

func main() {
	var resourcesClientFactory *armresources.ClientFactory
	resourceId := os.Getenv("RESOURCE_ID")

	subscriptionID := strings.Split(resourceId, "/")[2]

	cred, err := azidentity.NewDefaultAzureCredential(nil)
	if err != nil {
		log.Fatal(err)
	}

	ctx := context.Background()

	resourcesClientFactory, err = armresources.NewClientFactory(subscriptionID, cred, nil)
	if err != nil {
		log.Fatal(err)
	}

	resourcesClient = resourcesClientFactory.NewClient()

	if err != nil {
		log.Fatal(err)
	}
	resAPI := "2024-03-01"

	resp, err := resourcesClient.GetByID(
		ctx,
		resourceId,
		resAPI,
		nil)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(*resp.ID)


}
