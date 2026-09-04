OWNER := benvial
IMAGE_NAME := palace
REPO_URL := https://github.com/awslabs/palace.git
REGISTRY := ghcr.io/$(OWNER)
FULL_IMAGE := $(REGISTRY)/$(IMAGE_NAME)

VERSION ?= $(shell git ls-remote $(REPO_URL) refs/heads/main | cut -f1 | cut -c1-7)
TAG ?= dev
CUDA_ARCH ?= 80

.PHONY: info build tag push push-tag version all dev \
        info-gpu build-gpu tag-gpu push-gpu push-tag-gpu all-gpu dev-gpu

info:
	@echo "Building VERSION $(VERSION) with tag $(FULL_IMAGE):$(TAG)"

info-gpu:
	@echo "Building GPU VERSION $(VERSION) for sm$(CUDA_ARCH) with tag $(FULL_IMAGE):$(TAG)-gpu-sm$(CUDA_ARCH)"

login:
	echo $${GITHUB_TOKEN} | docker login ghcr.io -u $(OWNER) --password-stdin

build: info
	docker build \
		--build-arg VERSION=$(VERSION) \
		--build-arg GITHUB_TOKEN=$(GITHUB_TOKEN) \
		-t $(FULL_IMAGE):$(TAG) .

build-gpu: info-gpu
	docker build \
		-f Dockerfile-gpu \
		--build-arg VERSION=$(VERSION) \
		--build-arg GITHUB_TOKEN=$(GITHUB_TOKEN) \
		--build-arg CUDA_ARCH=$(CUDA_ARCH) \
		-t $(FULL_IMAGE):$(TAG)-gpu-sm$(CUDA_ARCH) .

tag:
	docker tag $(FULL_IMAGE):$(TAG) $(FULL_IMAGE):$(VERSION)

tag-gpu:
	docker tag $(FULL_IMAGE):$(TAG)-gpu-sm$(CUDA_ARCH) $(FULL_IMAGE):$(VERSION)-gpu-sm$(CUDA_ARCH)

push:
	docker push $(FULL_IMAGE):$(TAG)
	docker push $(FULL_IMAGE):$(VERSION)

push-tag:
	docker push $(FULL_IMAGE):$(TAG)

push-gpu:
	docker push $(FULL_IMAGE):$(TAG)-gpu-sm$(CUDA_ARCH)
	docker push $(FULL_IMAGE):$(VERSION)-gpu-sm$(CUDA_ARCH)

push-tag-gpu:
	docker push $(FULL_IMAGE):$(TAG)-gpu-sm$(CUDA_ARCH)

version:
	@echo $(VERSION)

all: build tag push
all-gpu: build-gpu tag-gpu push-gpu

# dev builds: push only the moving :dev tag, no VERSION tag to pile up
dev: build push-tag
dev-gpu: build-gpu push-tag-gpu