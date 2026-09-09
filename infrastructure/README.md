# Infrastructure deployment

The Bicep template in this directory provisions the Cloud Resume Challenge resource group at subscription scope.

## Scope

This first deployment creates only the development resource group:

- Name: rg-cloudresume-dev-eus2
- Region: East US 2
- Tags: Project, Environment, ManagedBy, and Owner

No paid services or billable SKUs are provisioned by this template.

## Prerequisites

- Azure CLI with the Bicep extension available
- An authenticated Azure account with permission to create resource groups in the target subscription
- The desired subscription selected with az account set

## Preview

Run a what-if deployment from this directory before deploying:

~~~sh
az deployment sub what-if \
  --name cloudresume-rg-whatif \
  --location eastus2 \
  --template-file main.bicep \
  --parameters main.bicepparam
~~~

Review the result. It should show one resource-group creation and no deletions or SKU changes.

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
