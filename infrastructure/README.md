# Infrastructure deployment

The Bicep template in this directory provisions the Cloud Resume Challenge resource group at subscription scope.

## Scope

This deployment creates the development resource group, static-website storage account, and visitor-counter database:

- Name: rg-cloudresume-dev-eus2
- Region: East US 2
- Tags: Project, Environment, ManagedBy, and Owner
- Storage: StorageV2, Standard_LRS, Hot access tier, HTTPS-only, TLS 1.2, and static website hosting with index.html as the default document
- Optional Azure Storage custom-domain registration, configured through CUSTOM_DOMAIN_NAME and REGISTER_STORAGE_CUSTOM_DOMAIN
- Cosmos DB for NoSQL: one East US 2 region, lifetime free tier enabled, and a shared-throughput `cloudresume` database at 1,000 RU/s with a `visitor-counter` container
- Visitor counter data: a Cosmos DB Built-in Data Contributor assignment for the deploying identity and an idempotent seed command that creates `{ "id": "resume", "count": 0 }`

The Standard_LRS storage account is usage-billed. Cosmos DB is capped at 1,000 RU/s and uses the lifetime free tier's first 1,000 RU/s and 25 GB allowance. No capacity beyond these limits is provisioned. Only one free-tier Cosmos DB account is allowed per subscription; if it has already been used, the deployment fails rather than creating a paid account.

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

Review the result. It should show one resource-group creation, one Standard_LRS storage-account creation, one Storage Blob Data Contributor assignment scoped to that account, one Cosmos DB for NoSQL account, one shared-throughput database at 1,000 RU/s, one visitor-counter container, one Cosmos DB Built-in Data Contributor assignment, and no deletions or SKU changes. If .env is not loaded, the role assignments are skipped.

## Deploy

After reviewing the what-if output, create the resource group:

~~~sh
./deploy.sh deploy
~~~

The deployment is incremental by default. Do not use complete mode.

## Seed the visitor counter

Install the pinned backend dependencies in your active virtual environment, then run the seed command after a successful deployment:

~~~sh
python3 -m pip install -r ../requirements.txt
./deploy.sh seed-counter
~~~

The command uses the signed-in Azure CLI identity and the Cosmos DB Built-in Data Contributor role from Bicep. It creates the document `{ "id": "resume", "count": 0 }` in the `/id` partition only when it does not exist. Re-running the command preserves the current count. A new Cosmos DB data-plane role assignment can take a few minutes to propagate.

## Publish the frontend

After a successful deployment, publish the contents of the repository's frontend directory to the static website's $web container:

~~~sh
./deploy.sh publish
~~~

The command reads the storage-account name from the `cloudresume-rg-deploy` Bicep deployment output, then uses Azure CLI data-plane authentication to upload the **contents** of `frontend/`. `frontend/` itself is not created as a path in $web: `frontend/index.html` becomes `$web/index.html`, and `frontend/css/style.css` becomes `$web/css/style.css`. It overwrites blobs in $web with matching names. The deploying identity must have the Storage Blob Data Contributor role assigned by the Bicep deployment; allow a few minutes for a new role assignment to propagate.
