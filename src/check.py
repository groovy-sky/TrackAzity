import ipaddress  
  
def get_minimum_networks(cidr_network):  
    network = ipaddress.ip_network(cidr_network)  
    subnet = network.prefixlen  
  
    minimum_networks = []  
  
    for i in range(1, 17):  
        subnet_size = subnet + i  
        if subnet_size > 32:  
            break  
  
        # Determine the network IP for the current subnet size  
        subnet_networks = list(network.subnets(new_prefix=subnet_size))  
        minimum_networks.extend(str(subnet_net) for subnet_net in subnet_networks)  
  
    return minimum_networks  
  
  
cidr = "192.168.0.0/24"  
minimum_networks = get_minimum_networks(cidr)  
print(minimum_networks)  
