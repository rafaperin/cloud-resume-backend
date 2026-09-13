targetScope = 'resourceGroup'

@description('Globally unique name of the Azure Cosmos DB account.')
@minLength(3)
@maxLength(44)
param cosmosAccountName string

@description('Azure region for the Cosmos DB account.')
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

@description('Microsoft Entra object ID of the user who initializes the visitor counter.')
param deployerPrincipalId string

var tableName = 'visitorcounter'
var provisionedThroughput = 400
var cosmosDataContributorRoleDefinitionId = '${cosmosAccount.id}/tableRoleDefinitions/00000000-0000-0000-0000-000000000002'
var hasDeployerPrincipalId = deployerPrincipalId != '00000000-0000-0000-0000-000000000000'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  tags: {
    Project: projectTag
    Environment: environmentTag
    ManagedBy: 'iac'
    Owner: ownerTag
  }
  properties: {
    capabilities: [
      {
        name: 'EnableTable'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableFreeTier: true
    enableMultipleWriteLocations: false
    isVirtualNetworkFilterEnabled: false
    locations: [
      {
        failoverPriority: 0
        isZoneRedundant: false
        locationName: location
      }
    ]
    publicNetworkAccess: 'Enabled'
    capacity: {
      totalThroughputLimit: provisionedThroughput
    }
  }
}

resource visitorCounterTable 'Microsoft.DocumentDB/databaseAccounts/tables@2024-05-15' = {
  parent: cosmosAccount
  name: tableName
  properties: {
    options: {
      throughput: provisionedThroughput
    }
    resource: {
      id: tableName
    }
  }
}

resource deployerCosmosDataContributor 'Microsoft.DocumentDB/databaseAccounts/tableRoleAssignments@2025-05-01-preview' = if (hasDeployerPrincipalId) {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, deployerPrincipalId, cosmosDataContributorRoleDefinitionId)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: cosmosDataContributorRoleDefinitionId
    scope: cosmosAccount.id
  }
}

output cosmosAccountId string = cosmosAccount.id
output cosmosAccountName string = cosmosAccount.name
output cosmosTableEndpoint string = 'https://${cosmosAccount.name}.table.cosmos.azure.com:443/'
output cosmosTableName string = visitorCounterTable.name
