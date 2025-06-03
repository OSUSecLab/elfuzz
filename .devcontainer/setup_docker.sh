#!/bin/bash -x

# this only works if the docker group does not already exist

DOCKER_SOCKET=/var/run/docker.sock
DOCKER_GROUP=docker

if [ -S ${DOCKER_SOCKET} ]; then
    DOCKER_GID=$(stat -c '%g' ${DOCKER_SOCKET})
    groupadd -for -g ${DOCKER_GID} ${DOCKER_GROUP}
    usermod -aG ${DOCKER_GROUP} appuser
fi

sudo chown appuser:appuser /tmp/fuzzdata
sudo chmod 777 /tmp/fuzzdata
