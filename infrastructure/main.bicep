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

@description('Optional custom subdomain for the static website, without a scheme or path. When set, Bicep manages the Azure Storage custom-domain mapping.')
param customDomainName string = ''

var storageAccountName = 'stcrdeveus2${take(uniqueString(subscription().id, resourceGroupName), 11)}'
var functionStorageAccountName = 'stfuncdeveus2${take(uniqueString(subscription().id, resourceGroupName), 11)}'
var cosmosAccountName = 'cosmos-cloudresume-dev-eus2-${take(uniqueString(subscription().id, resourceGroupName), 11)}'
var functionAppName = 'func-cr-dev-eus2-${take(uniqueString(subscription().id, resourceGroupName), 11)}'
var functionPlanName = 'plan-cr-dev-eus2'
var functionAppResourceId = '${subscription().id}/resourceGroups/${resourceGroupName}/providers/Microsoft.Web/sites/${functionAppName}'

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

module functionStorage './function-storage.bicep' = {
  name: 'functionStorageDeployment'
  scope: resourceGroup
  params: {
    storageAccountName: functionStorageAccountName
    location: location
    projectTag: projectTag
    environmentTag: environmentTag
    ownerTag: ownerTag
  }
}

module functionApp './function-app.bicep' = {
  name: 'functionAppDeployment'
  scope: resourceGroup
  params: {
    functionAppName: functionAppName
    functionPlanName: functionPlanName
    location: location
    projectTag: projectTag
    environmentTag: environmentTag
    ownerTag: ownerTag
    storageAccountName: functionStorage.outputs.storageAccountName
    storageBlobEndpoint: functionStorage.outputs.blobEndpoint
    deploymentContainerName: functionStorage.outputs.deploymentContainerName
    cosmosTableEndpoint: 'https://${cosmosAccountName}.table.cosmos.azure.com:443/'
    cosmosTableName: 'visitorcounter'
    frontendOrigin: empty(customDomainName) ? '' : 'https://${customDomainName}'
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
    deployerPrincipalId: deployerPrincipalId
    functionAppPrincipalId: functionApp.outputs.functionAppPrincipalId
    functionAppResourceId: functionAppResourceId
  }
}

output resourceGroupName string = resourceGroup.name
output resourceGroupLocation string = resourceGroup.location
output storageAccountName string = storageAccount.outputs.storageAccountName
output staticWebsiteUrl string = storageAccount.outputs.staticWebsiteUrl
output functionAppName string = functionApp.outputs.functionAppName
output functionAppUrl string = functionApp.outputs.functionAppUrl
output customDomainName string = storageAccount.outputs.customDomainName
output cosmosAccountName string = cosmosDb.outputs.cosmosAccountName
output cosmosTableEndpoint string = cosmosDb.outputs.cosmosTableEndpoint
output cosmosTableName string = cosmosDb.outputs.cosmosTableName
