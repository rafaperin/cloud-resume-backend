targetScope = 'resourceGroup'

@description('Globally unique name of the storage account.')
@minLength(3)
@maxLength(24)
param storageAccountName string

@description('Azure region for the storage account.')
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

@description('Microsoft Entra object ID of the user who deploys frontend files.')
param deployerPrincipalId string

@description('Principal ID of the frontend GitHub Actions deployment identity.')
param frontendDeploymentPrincipalId string = ''

var storageBlobDataContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)

var hasDeployerPrincipalId = deployerPrincipalId != '00000000-0000-0000-0000-000000000000'
var hasFrontendDeploymentPrincipalId = !empty(frontendDeploymentPrincipalId)
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

resource storageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (hasDeployerPrincipalId) {
  scope: storageAccount
  name: guid(storageAccount.id, deployerPrincipalId, storageBlobDataContributorRoleDefinitionId)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
    principalType: 'User'
  }
}

resource frontendStorageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (hasFrontendDeploymentPrincipalId) {
  scope: storageAccount
  name: guid(storageAccount.id, frontendDeploymentPrincipalId, storageBlobDataContributorRoleDefinitionId)
  properties: {
    principalId: frontendDeploymentPrincipalId
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-08-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    staticWebsite: {
      enabled: true
      defaultIndexDocumentPath: 'index.html'
      errorDocument404Path: '404.html'
    }
  }
}

output storageAccountName string = storageAccount.name
output staticWebsiteUrl string = storageAccount.properties.primaryEndpoints.web
