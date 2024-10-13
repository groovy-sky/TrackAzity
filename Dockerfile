# Use the official Python image based on Alpine Linux as the base image  
FROM python:3.10-alpine
  
RUN pip install --upgrade pip setuptools  

# Install Rust and Cargo  
RUN apk add --no-cache rust cargo 

# Copy the requirements.txt file to the container  
COPY requirements.txt .  
  
# Install the required Python packages  
RUN apk add --no-cache --virtual .build-deps build-base && pip install --no-cache-dir -r requirements.txt && apk del .build-deps  

WORKDIR /app  
  
# Copy the Python script to the container  
COPY src/ .  
  
# Run the Python script when the container starts  
CMD ["python", "app.py"]  
