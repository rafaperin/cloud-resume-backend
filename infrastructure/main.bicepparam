using './main.bicep'

param resourceGroupName = 'rg-cloudresume-dev-eus2'
param location = 'eastus2'
param projectTag = 'cloud-resume-challenge'
param environmentTag = 'dev'
param ownerTag = 'rafael-ferreira'
param deployerPrincipalId = readEnvironmentVariable('DEPLOYER_PRINCIPAL_ID', '00000000-0000-0000-0000-000000000000')
param customDomainName = readEnvironmentVariable('CUSTOM_DOMAIN_NAME', '')
param frontendGitHubOidcSubject = readEnvironmentVariable('FRONTEND_GITHUB_OIDC_SUBJECT', '')
