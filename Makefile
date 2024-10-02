IMAGE_NAME = gr00vysky/trackazity  
  
.PHONY: build run clean  
  
build:  
	cd Container && docker buildx build --push --platform linux/amd64,linux/arm64 -t $(IMAGE_NAME) .
  
run:  
	docker run -it --rm $(IMAGE_NAME)  
  
clean:  
	docker image rm $(IMAGE_NAME)  
