#!/bin/bash
# avoid hugging face libraries trying to connect to the internet:
# https://github.com/huggingface/transformers/issues/30345
HF_HUB_OFFLINE=1 uv run src/amica_main_loop.py $1

