#!/usr/bin/env bash

pip install -r requirements.txt

rm -rf ~/.cache/ms-playwright

python -m playwright install chromium