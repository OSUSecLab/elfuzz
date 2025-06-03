#!/usr/bin/env xonsh

import sys
import platform

match platform.system():
  case 'Darwin': 
    cpus = 8
  case _:
    cpus = int($(nproc)) - 5

assert cpus > 0

if len(sys.argv) >= 2 and sys.argv[1] == '--persist':
  docker run -m 150G --cpus @(cpus) -it --add-host=host.docker.internal:host-gateway -w /home/appuser/elmfuzz -v ".:/home/appuser/elmfuzz:rw" -v "/tmp/fuzzdata:/tmp/fuzzdata" -v "/var/run/docker.sock:/var/run/docker.sock" ghcr.io/cychen2021/elmfuzz-dev:24.08 /usr/bin/bash
else:
  docker run --rm -m 150G --cpus @(cpus) -it --add-host=host.docker.internal:host-gateway -w /home/appuser/elmfuzz -v ".:/home/appuser/elmfuzz:rw" -v "/tmp/fuzzdata:/tmp/fuzzdata" -v "/var/run/docker.sock:/var/run/docker.sock" ghcr.io/cychen2021/elmfuzz-dev:24.08 /usr/bin/bash
