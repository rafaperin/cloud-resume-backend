# Infrastructure deployment

The Bicep template in this directory provisions the Cloud Resume Challenge resource group at subscription scope.

## Scope

This deployment creates the development resource group and its storage account:

- Name: rg-cloudresume-dev-eus2
- Region: East US 2
- Tags: Project, Environment, ManagedBy, and Owner
- Storage: StorageV2, Standard_LRS, Hot access tier, HTTPS-only, TLS 1.2, and static website hosting with index.html as the default document

The Standard_LRS storage account is usage-billed. It is the lowest-cost replication option requested for this project; review the Azure estimate before running the deployment.

## Prerequisites

- Azure CLI with the Bicep extension available
- An authenticated Azure account with permission to create resource groups in the target subscription
- The desired subscription selected with az account set
- A root .env file containing the Microsoft Entra object ID of the user who uploads frontend files

Copy .env.example to .env if it does not already exist, then set DEPLOYER_PRINCIPAL_ID to the object ID returned by:

~~~sh
az ad signed-in-user show --query id --output tsv
~~~

Load the ignored environment file before running either deployment command:

~~~sh
set -a
source ../../.env
set +a
~~~

## Preview

Run a what-if deployment from this directory before deploying:

~~~sh
az deployment sub what-if \
  --name cloudresume-rg-whatif \
  --location eastus2 \
  --template-file main.bicep \
  --parameters main.bicepparam
~~~

Review the result. It should show one resource-group creation, one Standard_LRS storage-account creation, one Storage Blob Data Contributor assignment scoped to that account, and no deletions or SKU changes.

## Deploy

After reviewing the what-if output, create the resource group:

~~~sh
az deployment sub create \
  --name cloudresume-rg-deploy \
  --location eastus2 \
  --template-file main.bicep \
  --parameters main.bicepparam
~~~

The deployment is incremental by default. Do not use complete mode.
