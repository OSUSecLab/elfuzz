#!/usr/bin/env bash

# Share cache directory
volume=/projects/bdil/cchen26/hf_model
# HF token
HUGGIN_FACE_HUB_TOKEN=$(cat ${HOME}/.config/huggingface/token)

CONTAINER_HOME=/projects/bdil/cchen26/containers

# Code Llama: 8193, GPUs 2,3
model=codellama/CodeLlama-13b-hf

apptainer run --nv --env HUGGING_FACE_HUB_TOKEN=$HUGGIN_FACE_HUB_TOKEN --env PORT=$PORT --bind $volume:/data:rw $CONTAINER_HOME/text-generation-inference_1.4.5.sif \
--model-id $model \
--trust-remote-code --dtype bfloat16 \
--max-total-tokens 8192 --max-input-length 8000 --max-batch-prefill-tokens 8000 --enable-cuda-graphs --sharded false
