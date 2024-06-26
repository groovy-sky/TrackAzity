Add-AzAccount -identity
    
# Define the VNet ID and fails if not set
$vnetId = $env:VNET_ID
if(-not $vnetId){
    Write-Error "VNET_ID is not set"
    exit 1
}

# Define the MS Teams webhook URL  
$webhookUrl = $env:WEBHOOK_URL

# Select your subscription  
Select-AzSubscription -SubscriptionId $vnetId.Split('/')[2]

# Get the specific VNet by its ID  
$vnet = Get-AzResource -Id $vnetId -ExpandProperties  
  
# Get the peerings for the VNet  
$peerings = Get-AzVirtualNetworkPeering -VirtualNetworkName $vnet.Name -ResourceGroupName $vnet.ResourceGroupName  
  
# Loop through each peering  
foreach($peering in $peerings){  
    # Check if the peering state is 'Disconnected'  
    if($peering.PeeringState -eq 'Disconnected'){  
        # Remove the disconnected peering  
        Remove-AzVirtualNetworkPeering -Name $peering.Name -VirtualNetworkName $vnet.Name -ResourceGroupName $vnet.ResourceGroupName -Force  
        Write-Host "Removed the disconnected peering: " $peering.Name  
  
        $jsonBody = ConvertTo-Json -InputObject @{  
        text = "Removed remote VNet ID:`n`r" + $peering.Id + "`n`rRemote VNet Address Space:`n`r" + $peering.RemoteVirtualNetworkAddressSpace.AddressPrefixes
    }  
    # Send the JSON body to the MS Teams webhook if it is set
    if($webhookUrl){
    Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $jsonBody -ContentType 'application/json'  
    }
    }  
}