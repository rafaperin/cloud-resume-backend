# GitHub Actions OIDC bootstrap

The backend workflow deploys Azure resources with GitHub Actions OpenID Connect (OIDC). It does not use a client secret, publish profile, or stored Azure access key.

## One-time Azure setup

Create the user-assigned deployment identity in the existing Cloud Resume resource group, then grant it the subscription-scoped permissions required by the subscription-scoped Bicep deployment and its role assignments:

~~~sh
az identity create \
  --resource-group rg-cloudresume-dev-eus2 \
  --name id-cloudresume-github \
  --location eastus2
~~~

Assign `Contributor` and `Role Based Access Control Administrator` at the selected subscription scope. The latter is required because the Bicep templates create Azure role assignments. Also assign `Website Contributor` at the Function App scope so the Functions deployment action can publish code. Restrict this identity further with a custom role when the infrastructure scope is stable.

Create a federated credential that trusts only the `main` branch of `rafaperin/cloud-resume-backend`, with issuer `https://token.actions.githubusercontent.com` and audience `api://AzureADTokenExchange`. Use GitHub's current immutable OIDC subject format for this repository when creating the credential.

## GitHub Actions configuration

Configure these repository secrets from the deployment identity and selected Azure subscription:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

Configure the deployment principal as a repository secret, because Bicep reads it from an environment variable during workflow execution:

- `DEPLOYER_PRINCIPAL_ID`

Configure these repository variables for the non-secret Bicep configuration:

- `CUSTOM_DOMAIN_NAME`

Do not commit any of these values. The workflow reads them only at deployment time.

## Deployment policy

Pull requests run the test and Bicep-validation jobs only. A push to `main` runs deployment after both jobs succeed. Configure branch protection after the workflow has completed its first run, requiring the `Test backend` and `Validate Bicep` checks before merge.
