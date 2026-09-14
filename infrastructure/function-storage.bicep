targetScope = 'resourceGroup'

@description('Globally unique name of the storage account used by Azure Functions.')
@minLength(3)
@maxLength(24)
param storageAccountName string

@description('Azure region for the Function App storage account.')
@allowed([
  'eastus2'
])
param location string

@description('Value for the Project resource tag.')
param projectTag string

@description('Value for the Environment resource tag.')
param environmentTag string

@description('Value for the Owner resource tag.')
param ownerTag string

var deploymentContainerName = 'function-releases'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  tags: {
    Project: projectTag
    Environment: environmentTag
    ManagedBy: 'iac'
    Owner: ownerTag
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-08-01' = {
  parent: storageAccount
  name: 'default'
}

resource deploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-08-01' = {
  parent: blobService
  name: deploymentContainerName
  properties: {
    publicAccess: 'None'
  }
}

output storageAccountName string = storageAccount.name
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output deploymentContainerName string = deploymentContainer.name
