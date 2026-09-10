#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  printf '%s\n' 'Usage: ./deploy.sh <what-if|deploy>' >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
environment_file="$project_root/.env"
action="$1"

if [[ ! -f "$environment_file" ]]; then
  printf '%s\n' 'Missing root .env file. Copy .env.example to .env and set DEPLOYER_PRINCIPAL_ID.' >&2
  exit 1
fi

set -a
source "$environment_file"
set +a

if [[ -z "$DEPLOYER_PRINCIPAL_ID" ]]; then
  printf '%s\n' 'DEPLOYER_PRINCIPAL_ID must be set in .env.' >&2
  exit 1
fi

case "$action" in
  what-if)
    operation='what-if'
    deployment_name='cloudresume-rg-whatif'
    ;;
  deploy)
    operation='create'
    deployment_name='cloudresume-rg-deploy'
    ;;
  *)
    printf '%s\n' 'Usage: ./deploy.sh <what-if|deploy>' >&2
    exit 1
    ;;
esac

az deployment sub "$operation" \
  --name "$deployment_name" \
  --location eastus2 \
  --template-file "$script_dir/main.bicep" \
  --parameters "$script_dir/main.bicepparam"
