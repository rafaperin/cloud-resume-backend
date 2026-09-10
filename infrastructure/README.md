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

The Bicep editor does not load .env files automatically. The parameter file uses a non-secret sentinel GUID so editor validation succeeds. Use deploy.sh for all deployments; it verifies and loads the root .env file before calling Azure CLI.

## Preview

Run a what-if deployment from this directory before deploying:

~~~sh
./deploy.sh what-if
~~~

Review the result. It should show one resource-group creation, one Standard_LRS storage-account creation, one Storage Blob Data Contributor assignment scoped to that account, and no deletions or SKU changes. If .env is not loaded, the role assignment is skipped.

## Deploy

After reviewing the what-if output, create the resource group:

~~~sh
./deploy.sh deploy
~~~

The deployment is incremental by default. Do not use complete mode.

## Publish the frontend

After a successful deployment, publish the contents of the repository's frontend directory to the static website's $web container:

~~~sh
./deploy.sh publish
~~~

The command reads the storage-account name from the `cloudresume-rg-deploy` Bicep deployment output, then uses Azure CLI data-plane authentication to upload the **contents** of `frontend/`. `frontend/` itself is not created as a path in $web: `frontend/index.html` becomes `$web/index.html`, and `frontend/css/style.css` becomes `$web/css/style.css`. It overwrites blobs in $web with matching names. The deploying identity must have the Storage Blob Data Contributor role assigned by the Bicep deployment; allow a few minutes for a new role assignment to propagate.
