import csv    
import threading    
import ipaddress    
    
class IpManager:    
    def __init__(self, csv_file):    
        self.lock = threading.Lock()    
        self.csv_file = csv_file    
        self.ip_ranges = self.load_from_csv(csv_file)    
    
    def load_from_csv(self, csv_file):    
        ip_ranges = []    
        with open(csv_file, 'r') as csvfile:    
            reader = csv.DictReader(csvfile, delimiter='|')    
            for row in reader:    
                ip_range = ipaddress.ip_network(row['IP'])    
                subscription_id = row['subscriptionId']    
                network_name = row['NetworkName']    
                peering_state = row['peeringState']    
                peering_sync_level = row['peeringSyncLevel']    
                ip_ranges.append({    
                    "ip_range": ip_range,    
                    "subscription_id": subscription_id,    
                    "network_name": network_name,    
                    "peering_state": peering_state,    
                    "peering_sync_level": peering_sync_level    
                })    
        return ip_ranges    
    
    def find_available_range(self, required_size):    
        for ip_range in self.ip_ranges:    
            if ip_range["network_name"] == '' and ip_range["ip_range"].prefixlen <= required_size:    
                return ip_range    
        return None    
  
    def reserve_range(self, network_name, required_size, subscription_id, peering_state, peering_sync_level):    
        with self.lock:    
            ip_range = self.find_available_range(required_size)    
            if ip_range is None:    
                return None    
    
            # Update the reserved range    
            ip_range["network_name"] = network_name    
            ip_range["subscription_id"] = subscription_id    
            ip_range["peering_state"] = peering_state    
            ip_range["peering_sync_level"] = peering_sync_level    
    
            # Create new ranges for the leftover IPs    
            subnets = list(ip_range["ip_range"].subnets(new_prefix=required_size))    
            reserved_subnet = subnets.pop(0)    
            ip_range["ip_range"] = reserved_subnet    
    
            for subnet in subnets:    
                self.ip_ranges.append({    
                    "ip_range": subnet,    
                    "subscription_id": '',    
                    "network_name": '',    
                    "peering_state": '',    
                    "peering_sync_level": ''    
                })    
    
            # Save the updated ranges to the CSV file    
            self.save_to_csv()    
            return ip_range    
  
    def save_to_csv(self):    
        with open(self.csv_file, 'w', newline='') as csvfile:    
            fieldnames = ['IP', 'subscriptionId', 'NetworkName', 'peeringState', 'peeringSyncLevel']    
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')    
  
            writer.writeheader()    
            for ip_range in self.ip_ranges:    
                writer.writerow({    
                    'IP': str(ip_range["ip_range"]),    
                    'subscriptionId': ip_range["subscription_id"],    
                    'NetworkName': ip_range["network_name"],    
                    'peeringState': ip_range["peering_state"],    
                    'peeringSyncLevel': ip_range["peering_sync_level"]    
                })    
  
# Usage  
manager = IpManager('ip_ranges.csv')  
manager.reserve_range('Network2', 27, 'f406059a-f933-45e0-aefe-e37e0382d5de', 'Connected', 'FullyInSync')  