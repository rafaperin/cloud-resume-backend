targetScope = 'resourceGroup'

@description('Globally unique name of the Azure Function App.')
@minLength(2)
@maxLength(60)
param functionAppName string

@description('Name of the Azure Functions Flex Consumption plan.')
param functionPlanName string

@description('Azure region for the Function App and its plan.')
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

@description('Name of the storage account used by Azure Functions.')
param storageAccountName string

@description('Blob service endpoint of the Azure Functions storage account.')
param storageBlobEndpoint string

@description('Private blob container that stores Flex Consumption deployment packages.')
param deploymentContainerName string

@description('Azure Cosmos DB for Table endpoint for the visitor counter.')
param cosmosTableEndpoint string

@description('Azure Cosmos DB for Table table name for the visitor counter.')
param cosmosTableName string

@description('Allowed browser origin for the static resume site.')
param frontendOrigin string

var storageBlobDataOwnerRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
)

var allowedOrigins = empty(frontendOrigin) ? [] : [
  frontendOrigin
]

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource functionPlan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: functionPlanName
  location: location
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  tags: {
    Project: projectTag
    Environment: environmentTag
    ManagedBy: 'iac'
    Owner: ownerTag
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2024-04-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  tags: {
    Project: projectTag
    Environment: environmentTag
    ManagedBy: 'iac'
    Owner: ownerTag
  }
  properties: {
    httpsOnly: true
    serverFarmId: functionPlan.id
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storageBlobEndpoint}${deploymentContainerName}'
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
      runtime: {
        name: 'python'
        version: '3.13'
      }
      scaleAndConcurrency: {
        instanceMemoryMB: 512
        maximumInstanceCount: 10
      }
    }
    siteConfig: {
      alwaysOn: false
      cors: {
        allowedOrigins: allowedOrigins
        supportCredentials: false
      }
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccountName
        }
        {
          name: 'COSMOS_TABLE_ENDPOINT'
          value: cosmosTableEndpoint
        }
        {
          name: 'VISITOR_TABLE_NAME'
          value: cosmosTableName
        }
        {
          name: 'VISITOR_COUNTER_STORAGE'
          value: 'cosmos'
        }
      ]
    }
  }
}

resource functionStorageBlobDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, storageBlobDataOwnerRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataOwnerRoleDefinitionId
  }
}

output functionAppName string = functionApp.name
output functionAppPrincipalId string = functionApp.identity.principalId
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
