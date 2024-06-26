# Use Microsoft's Azure PowerShell base image  
FROM mcr.microsoft.com/azure-powershell:latest
  
# Copy the PowerShell script into the container  
COPY main.ps1 /
  
# When the container starts, run the PowerShell script 
ENTRYPOINT [ "pwsh", "-File", "/main.ps1"]