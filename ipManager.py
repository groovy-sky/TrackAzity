import csv    
import threading    
import ipaddress    
import argparse   
import hashlib  
  
class IpManager:    
    def __init__(self, csv_file):    
        self.lock = threading.Lock()    
        self.csv_file = csv_file    
        self.ip_ranges = self.load_from_csv(csv_file)    
    
    def find_available_range(self, required_size):    
        for ip_range in self.ip_ranges:    
            if ip_range["network_name"] == '' and ip_range["ip_range"].prefixlen <= required_size:    
                return ip_range    
        return None    
    
    def reserve_range(self, required_size):    
        with self.lock:    
            ip_range = self.find_available_range(required_size)    
            if ip_range is None:    
                return None    
        
            ip_range["network_name"] = "Reserved"    
            ip_range["hashed"] = hashlib.md5(str(ip_range["ip_range"]).encode()).hexdigest()  
        
            subnets = list(ip_range["ip_range"].subnets(new_prefix=required_size))    
            reserved_subnet = subnets.pop(0)    
            ip_range["ip_range"] = reserved_subnet    
        
            for subnet in subnets:    
                self.ip_ranges.append({    
                    "ip_range": subnet,    
                    "subscription_id": '',    
                    "network_name": '',    
                    "peering_state": '',    
                    "peering_sync_level": '',    
                    "hashed": None  
                })    
            self.save_to_csv()    
            return ip_range    
    
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
                hashed = hashlib.md5(str(ip_range).encode()).hexdigest() if network_name else None  
                ip_ranges.append({    
                    "ip_range": ip_range,    
                    "subscription_id": subscription_id,    
                    "network_name": network_name,    
                    "peering_state": peering_state,    
                    "peering_sync_level": peering_sync_level,  
                    "hashed": hashed  
                })    
        ip_ranges = sorted(ip_ranges, key=lambda k: int(ipaddress.IPv4Address(k['ip_range'].network_address)))    
        return ip_ranges  
    
    def save_to_csv(self):    
        with open(self.csv_file, 'w', newline='') as csvfile:    
            fieldnames = ['IP', 'subscriptionId', 'NetworkName', 'peeringState', 'peeringSyncLevel', 'Hashed']    
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')    
    
            writer.writeheader()    
            for ip_range in sorted(self.ip_ranges, key=lambda k: int(ipaddress.IPv4Address(k['ip_range'].network_address))):    
                writer.writerow({    
                    'IP': str(ip_range["ip_range"]),    
                    'subscriptionId': ip_range["subscription_id"],    
                    'NetworkName': ip_range["network_name"],    
                    'peeringState': ip_range["peering_state"],    
                    'peeringSyncLevel': ip_range["peering_sync_level"],  
                    'Hashed': ip_range["hashed"]  
                })   