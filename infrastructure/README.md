# Infrastructure deployment

The Bicep template in this directory provisions the Cloud Resume Challenge resource group at subscription scope.

## Scope

This deployment creates the development resource group, static-website storage account, visitor-counter table, and the serverless API infrastructure:

- Name: rg-cloudresume-dev-eus2
- Region: East US 2
- Tags: Project, Environment, ManagedBy, and Owner
- Frontend storage: StorageV2, Standard_LRS, Hot access tier, HTTPS-only, TLS 1.2, and static website hosting with `index.html` and `404.html` as its default and error documents
- Cloudflare-managed frontend custom domain, configured through `CUSTOM_DOMAIN_NAME` for Function App CORS
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
- A repository-root `.env` file containing the Microsoft Entra object ID used for local infrastructure deployment

Copy .env.example to .env if it does not already exist, then set DEPLOYER_PRINCIPAL_ID to the object ID returned by:

~~~sh
az ad signed-in-user show --query id --output tsv
~~~

The Bicep editor does not load .env files automatically. The parameter file uses a non-secret sentinel GUID so editor validation succeeds. Use deploy.sh for all deployments; it verifies and loads the root .env file before calling Azure CLI.

## Configure the frontend custom domain

Set `CUSTOM_DOMAIN_NAME` in the root `.env` to the public frontend **subdomain**, without `https://`, a path, or a port. Bicep uses this value only to configure the Function App CORS origin. It does not register a custom domain with Azure Storage.

Configure the public hostname and HTTPS in Cloudflare. Point the Cloudflare record to the static-website host:

~~~sh
az deployment sub show \
  --name cloudresume-rg-deploy \
  --query 'properties.outputs.staticWebsiteUrl.value' \
  --output tsv
~~~

Use a CNAME from `CUSTOM_DOMAIN_NAME` to that host and configure Cloudflare TLS for the visitor-facing endpoint. Azure Storage custom-domain validation is deliberately outside this deployment, so it cannot block backend updates.

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

Frontend files are deployed by the `cloud-resume-frontend` repository and its CI/CD pipeline. This backend deployment script never uploads static website files.
