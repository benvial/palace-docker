IMAGE_NAME := benvial/palace
REPO_URL := https://github.com/awslabs/palace.git
GIT_SHA ?= $(shell git ls-remote https://github.com/awslabs/palace.git refs/heads/main | cut -f1 | cut -c1-7)
TAG ?= dev

info:
	@echo building sha $(GIT_SHA) with tag $(IMAGE_NAME):$(TAG)


build: info
	docker build --build-arg GIT_SHA=$(GIT_SHA) -t $(IMAGE_NAME):$(TAG) .

tag:
	docker tag $(IMAGE_NAME):$(TAG) $(IMAGE_NAME):$(GIT_SHA)

push:
	docker push $(IMAGE_NAME):$(TAG)
	docker push $(IMAGE_NAME):$(GIT_SHA)


sha:
	@echo $(GIT_SHA)

all: build tag push

