#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  printf '%s\n' 'Usage: ./deploy.sh <what-if|deploy|publish>' >&2
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
  publish)
    storage_account_name="$(az deployment sub show \
      --name cloudresume-rg-deploy \
      --query 'properties.outputs.storageAccountName.value' \
      --output tsv)"

    if [[ -z "$storage_account_name" ]]; then
      printf '%s\n' 'Unable to determine the storage account. Run ./deploy.sh deploy first.' >&2
      exit 1
    fi

    az storage blob upload-batch \
      --account-name "$storage_account_name" \
      --auth-mode login \
      --destination '$web' \
      --source "$project_root/frontend" \
      --overwrite true
    exit 0
    ;;
  what-if)
    operation='what-if'
    deployment_name='cloudresume-rg-whatif'
    ;;
  deploy)
    operation='create'
    deployment_name='cloudresume-rg-deploy'
    ;;
  *)
    printf '%s\n' 'Usage: ./deploy.sh <what-if|deploy|publish>' >&2
    exit 1
    ;;
esac

az deployment sub "$operation" \
  --name "$deployment_name" \
  --location eastus2 \
  --template-file "$script_dir/main.bicep" \
  --parameters "$script_dir/main.bicepparam"
