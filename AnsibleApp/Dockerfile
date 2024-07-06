# Use an official Alpine runtime as a parent image    
FROM python:3.9.19-alpine   

# Set the working directory in the container    
WORKDIR /ansible  
  
# Copy the requirements file into the container    
COPY . .  

RUN apk add --no-cache \
		# build tools
		coreutils \
		g++ \
		gcc \
		linux-headers \
		make \
		musl-dev \
		openssl-dev \
		python3-dev \
        py3-cffi \
        libffi-dev && pip3 install ansible-core && ansible-galaxy collection install azure.azcollection && pip3 install -r requirements.txt
  
# Run ansible-playbook when the container launches    
CMD ["ansible", "-v"]  

# ansible-playbook test.yml -e az_resource_id="/subscriptions/20f105d9-0e32-43bb-bd88-3f616a393940/resourceGroups/exampleGroup/providers/Microsoft.Network/virtualNetworks/exampleVnet" -e az_resource_api="2023-11-01"
