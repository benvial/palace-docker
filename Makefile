OWNER := benvial
IMAGE_NAME := palace
REPO_URL := https://github.com/awslabs/palace.git
REGISTRY := ghcr.io/$(OWNER)
FULL_IMAGE := $(REGISTRY)/$(IMAGE_NAME)

VERSION ?= $(shell git rev-parse --short HEAD)
TAG ?= dev

.PHONY: info build tag push version all



info:
	@echo "Building VERSION $(VERSION) with tag $(FULL_IMAGE):$(TAG)"
	
login:
	echo $${GITHUB_TOKEN} | docker login ghcr.io -u $(OWNER) --password-stdin

build: info
	docker build --build-arg VERSION=$(VERSION) -t $(FULL_IMAGE):$(TAG) .

tag:
	docker tag $(FULL_IMAGE):$(TAG) $(FULL_IMAGE):$(VERSION)

push:
	docker push $(FULL_IMAGE):$(TAG)
	docker push $(FULL_IMAGE):$(VERSION)

version:
	@echo $(VERSION)

all: build tag push
