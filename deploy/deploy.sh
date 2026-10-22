#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

sam build
sam deploy "$@"

aws cloudformation describe-stacks --stack-name twice \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue" --output text
