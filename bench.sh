#!/usr/bin/env -S bash

set -xueo pipefail
uv run deny_check.py --count 10000 --mode rs > bench.txt
uv run deny_check.py --count 10000 --mode py >> bench.txt