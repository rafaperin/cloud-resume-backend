#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  printf '%s\n' 'Usage: ./deploy.sh <what-if|deploy|publish|seed-counter>' >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
environment_file="$project_root/.env"
frontend_source_directory="$project_root/frontend"
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

custom_domain_name="${CUSTOM_DOMAIN_NAME:-}"
register_storage_custom_domain="${REGISTER_STORAGE_CUSTOM_DOMAIN:-false}"

if [[ "$register_storage_custom_domain" != 'true' && "$register_storage_custom_domain" != 'false' ]]; then
  printf '%s\n' 'REGISTER_STORAGE_CUSTOM_DOMAIN must be true or false.' >&2
  exit 1
fi

if [[ "$register_storage_custom_domain" == 'true' && -z "$custom_domain_name" ]]; then
  printf '%s\n' 'CUSTOM_DOMAIN_NAME must be set when REGISTER_STORAGE_CUSTOM_DOMAIN is true.' >&2
  exit 1
fi

if [[ "$register_storage_custom_domain" == 'true' ]] && [[ ! "$custom_domain_name" =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$ ]]; then
  printf '%s\n' 'CUSTOM_DOMAIN_NAME must be a lowercase subdomain without a scheme, path, or port.' >&2
  exit 1
fi

case "$action" in
  publish)
    if [[ ! -d "$frontend_source_directory" ]]; then
      printf '%s\n' 'Missing frontend directory.' >&2
      exit 1
    fi

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
      --source "$frontend_source_directory" \
      --overwrite true
    ;;
  seed-counter)
    cosmos_table_endpoint="$(az deployment sub show \
      --name cloudresume-rg-deploy \
      --query 'properties.outputs.cosmosTableEndpoint.value' \
      --output tsv)"
    cosmos_table_name="$(az deployment sub show \
      --name cloudresume-rg-deploy \
      --query 'properties.outputs.cosmosTableName.value' \
      --output tsv)"

    if [[ -z "$cosmos_table_endpoint" || -z "$cosmos_table_name" ]]; then
      printf '%s\n' 'Unable to determine Cosmos DB Table API resources. Run ./deploy.sh deploy first.' >&2
      exit 1
    fi

    COSMOS_TABLE_ENDPOINT="$cosmos_table_endpoint" \
      VISITOR_TABLE_NAME="$cosmos_table_name" \
      python3 "$project_root/backend/tools/seed_visitor_counter.py"
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
    printf '%s\n' 'Usage: ./deploy.sh <what-if|deploy|publish|seed-counter>' >&2
    exit 1
    ;;
esac

if [[ "$action" == 'publish' || "$action" == 'seed-counter' ]]; then
  exit 0
fi

az deployment sub "$operation" \
  --name "$deployment_name" \
  --location eastus2 \
  --template-file "$script_dir/main.bicep" \
  --parameters "$script_dir/main.bicepparam"
