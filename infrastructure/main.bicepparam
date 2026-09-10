using './main.bicep'

param resourceGroupName = 'rg-cloudresume-dev-eus2'
param location = 'eastus2'
param projectTag = 'cloud-resume-challenge'
param environmentTag = 'dev'
param ownerTag = 'rafael-ferreira'
param deployerPrincipalId = readEnvironmentVariable('DEPLOYER_PRINCIPAL_ID')
