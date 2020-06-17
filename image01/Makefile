
WORKSPACE ?= $(realpath $(dir $(realpath $(firstword $(MAKEFILE_LIST)))))
IMAGE := ajarv/py-pandas

build-docker:
	docker build -t ${IMAGE} ${WORKSPACE}
	