#!/bin/bash
IMAGE_NAME=eu.gcr.io/p8-integrations-eu-dev-2/kafka-jupi
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
pushd $DIR
docker build -t ${IMAGE_NAME}  .
docker push ${IMAGE_NAME}
popd
