# Infrastructure deployment

The Bicep template in this directory provisions the Cloud Resume Challenge resource group at subscription scope.

## Scope

This deployment creates the development resource group, static-website storage account, visitor-counter table, and the serverless API infrastructure:

- Name: rg-cloudresume-dev-eus2
- Region: East US 2
- Tags: Project, Environment, ManagedBy, and Owner
- Frontend storage: StorageV2, Standard_LRS, Hot access tier, HTTPS-only, TLS 1.2, and static website hosting with `index.html` and `404.html` as its default and error documents
- Optional Azure Storage custom-domain registration, configured through CUSTOM_DOMAIN_NAME and REGISTER_STORAGE_CUSTOM_DOMAIN
- Cosmos DB Table API: one East US 2 region, lifetime free tier enabled, and a `visitorcounter` table at 400 RU/s
- Visitor counter data: a Cosmos DB Built-in Data Contributor assignment for the deploying identity and an idempotent seed command that creates `PartitionKey=resume`, `RowKey=counter`, and `Count=0`
- Azure Functions: a Linux Flex Consumption (`FC1`) plan and a Python 3.13 Function App with a system-assigned managed identity
- Function backing storage: a separate StorageV2, Standard_LRS account with a private `function-releases` blob container, accessed only through the Function App's managed identity
- Function data access: a Cosmos DB Built-in Data Contributor assignment for the Function App identity, scoped to the Table API account
- Function API configuration: `COSMOS_TABLE_ENDPOINT`, `VISITOR_TABLE_NAME`, and `VISITOR_COUNTER_STORAGE=cosmos` are supplied as application settings; CORS allows the configured custom-domain origin

The two Standard_LRS storage accounts are usage-billed. The separate Function backing account is required by Azure Functions and keeps runtime and deployment access away from the public website files. Cosmos DB is capped at 400 RU/s, the minimum manual provisioned throughput for this Table API workload. This remains within the lifetime free tier's first 1,000 RU/s and 25 GB allowance. No capacity beyond these limits is provisioned. Only one free-tier Cosmos DB account is allowed per subscription; if it has already been used, the deployment fails rather than creating a paid account.

The templates do not contain subscription IDs, tenant IDs, principal IDs, storage keys, connection strings, or deployment-specific resource names. The ignored root `.env` supplies the deploying user’s principal ID at deployment time. Root deployment outputs contain only the names and public endpoints required by `deploy.sh`; identity and resource IDs remain internal to the deployment.

The Function App uses 512 MB on-demand instances, has no always-ready instances, and is capped at 10 instances. Flex Consumption provides a monthly on-demand free grant of 250,000 executions and 100,000 GB-seconds per subscription, but it is a usage-billed service after that allowance. This configuration limits scale but does not impose a spending cap; review the Azure estimate before deployment.

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

## Configure a custom domain

Set `CUSTOM_DOMAIN_NAME` in the root `.env` to the custom **subdomain**, without `https://`, a path, or a port. The deployment defaults `REGISTER_STORAGE_CUSTOM_DOMAIN` to `false`, so Cloudflare-managed domains bypass Azure Storage's CNAME verification and do not block unrelated infrastructure updates.

If Azure Storage registration has already succeeded, leave `REGISTER_STORAGE_CUSTOM_DOMAIN=false` on future deployments to avoid re-running validation. The deployment will not request a new Storage custom-domain registration.

Set `REGISTER_STORAGE_CUSTOM_DOMAIN=true` only when a direct Azure Storage custom-domain registration is required. The domain must be a lowercase subdomain, such as `www.example.com`; root domains, such as `example.com`, are not supported by Azure Storage custom-domain mapping.

Before running `./deploy.sh deploy` with registration enabled, create a public **DNS-only** CNAME record in Cloudflare for `asverify.<CUSTOM_DOMAIN_NAME>` that targets `asverify.<static-website-host>`. Obtain the static-website host from the deployment output:

~~~sh
az deployment sub show \
  --name cloudresume-rg-deploy \
  --query 'properties.outputs.staticWebsiteUrl.value' \
  --output tsv
~~~

After Bicep registers the domain, replace the temporary validation record with a CNAME from `CUSTOM_DOMAIN_NAME` to the static-website host. You can then proxy that record through Cloudflare to provide visitor-facing HTTPS and redirects. Azure must be able to resolve the temporary validation record publicly.

Azure Storage does not provide a certificate for the custom domain. Configure Cloudflare to use an encrypted origin connection; do not use Flexible mode because this storage account requires HTTPS. Full (strict) requires an origin certificate that matches the custom domain, which Azure Storage does not provide.

## Preview

Run a what-if deployment from this directory before deploying:

~~~sh
./deploy.sh what-if
~~~

Review the result. It should show one resource-group creation, two Standard_LRS storage accounts, the private Function `function-releases` container, one Flex Consumption plan, one Function App with its system-assigned identity, Function App storage and Cosmos data-plane role assignments, one Cosmos DB Table API account, one `visitorcounter` table at 400 RU/s, and no deletions or SKU changes.

## Deploy

After reviewing the what-if output, create the resource group:

~~~sh
./deploy.sh deploy
~~~

The deployment is incremental by default. Do not use complete mode.

## Function API infrastructure

The Bicep deployment configures the public Function App that will expose `GET /api/visitor` and `POST /api/visitor` once the Python function code is added and published. Its URL is available after deployment:

~~~sh
az deployment sub show \
  --name cloudresume-rg-deploy \
  --query 'properties.outputs.functionAppUrl.value' \
  --output tsv
~~~

Flex Consumption requires a OneDeploy package in the private `function-releases` container in the Function backing storage account. Provisioning infrastructure does not publish function source code. Publish the Python Function App in a later step after its implementation and deployment workflow are in place.

## Seed the visitor counter

Install the pinned backend dependencies in your active virtual environment, then run the seed command after a successful deployment:

~~~sh
python3 -m pip install -r ../requirements.txt
./deploy.sh seed-counter
~~~

The command uses the signed-in Azure CLI identity and the Cosmos DB Built-in Data Contributor role from Bicep. It creates the entity with `PartitionKey=resume`, `RowKey=counter`, and `Count=0` only when it does not exist. Re-running the command preserves the current count. A new Cosmos DB data-plane role assignment can take a few minutes to propagate.

Azure Cosmos DB account APIs cannot be changed after creation. If a NoSQL API account from an earlier deployment exists, do not delete it automatically. Obtain explicit approval before deleting that account and recreating it with the Table API.

## Publish the frontend

After a successful deployment, publish the contents of the repository's frontend directory to the static website's $web container:

~~~sh
./deploy.sh publish
~~~

The command reads the storage-account name from the `cloudresume-rg-deploy` Bicep deployment output, then uses Azure CLI data-plane authentication to upload the **contents** of `frontend/`. `frontend/` itself is not created as a path in $web: `frontend/index.html` becomes `$web/index.html`, and `frontend/css/style.css` becomes `$web/css/style.css`. It overwrites blobs in $web with matching names. The deploying identity must have the Storage Blob Data Contributor role assigned by the Bicep deployment; allow a few minutes for a new role assignment to propagate.
