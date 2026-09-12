targetScope = 'subscription'

@description('Name of the resource group that contains the Cloud Resume Challenge resources.')
@minLength(1)
param resourceGroupName string = 'rg-cloudresume-dev-eus2'

@description('Azure region for the resource group and all project resources.')
@allowed([
  'eastus2'
])
param location string = 'eastus2'

@description('Value for the Project resource tag.')
param projectTag string = 'cloud-resume-challenge'

@description('Value for the Environment resource tag.')
param environmentTag string = 'dev'

@description('Value for the Owner resource tag.')
param ownerTag string = 'rafael-ferreira'

@description('Microsoft Entra object ID of the user who deploys frontend files.')
@minLength(1)
param deployerPrincipalId string

@description('Optional custom subdomain to register for the static website, without a scheme or path.')
param customDomainName string = ''

var storageAccountName = 'stcrdeveus2${take(uniqueString(subscription().id, resourceGroupName), 11)}'
var cosmosAccountName = 'cosmos-cloudresume-dev-eus2-${take(uniqueString(subscription().id, resourceGroupName), 11)}'

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: {
    Project: projectTag
    Environment: environmentTag
    ManagedBy: 'iac'
    Owner: ownerTag
  }
}

module storageAccount './storage.bicep' = {
  name: 'storageAccountDeployment'
  scope: resourceGroup
  params: {
    storageAccountName: storageAccountName
    location: location
    projectTag: projectTag
    environmentTag: environmentTag
    ownerTag: ownerTag
    deployerPrincipalId: deployerPrincipalId
    customDomainName: customDomainName
  }
}

module cosmosDb './cosmos-db.bicep' = {
  name: 'cosmosDbDeployment'
  scope: resourceGroup
  params: {
    cosmosAccountName: cosmosAccountName
    location: location
    projectTag: projectTag
    environmentTag: environmentTag
    ownerTag: ownerTag
  }
}

output resourceGroupId string = resourceGroup.id
output resourceGroupName string = resourceGroup.name
output resourceGroupLocation string = resourceGroup.location
output storageAccountId string = storageAccount.outputs.storageAccountId
output storageAccountName string = storageAccount.outputs.storageAccountName
output staticWebsiteUrl string = storageAccount.outputs.staticWebsiteUrl
output customDomainName string = storageAccount.outputs.customDomainName
output cosmosAccountId string = cosmosDb.outputs.cosmosAccountId
output cosmosAccountName string = cosmosDb.outputs.cosmosAccountName
output cosmosEndpoint string = cosmosDb.outputs.cosmosEndpoint
output cosmosDatabaseName string = cosmosDb.outputs.cosmosDatabaseName
output cosmosContainerName string = cosmosDb.outputs.cosmosContainerName
