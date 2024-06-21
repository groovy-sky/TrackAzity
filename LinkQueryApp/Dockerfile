# Start from the official Golang image  
FROM golang:1.22 AS builder  
  
ARG TARGETPLATFORM  
ARG BUILDPLATFORM  
  
# Create a directory for the application  
WORKDIR /app  
  
# Copy the local package files to the container's workspace  
ADD . /app  
  
# Build the application  
RUN CGO_ENABLED=0 GOOS=linux GOARCH=$(echo ${TARGETPLATFORM} | cut -d / -f2) go build -a -installsuffix cgo -o main .  
  
# Use scratch image  
FROM scratch  
  
# Copy the binary from builder  
COPY --from=builder /app/main /main  
  
# Copy SSL certificates  
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/  
  
# Set the entrypoint  
ENTRYPOINT ["/main"] 