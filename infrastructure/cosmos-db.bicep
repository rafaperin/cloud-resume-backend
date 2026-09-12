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

var databaseName = 'cloudresume'
var containerName = 'visitor-counter'
var sharedThroughput = 1000

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
    capabilities: []
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
      totalThroughputLimit: sharedThroughput
    }
  }
}

resource visitorCounterDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    options: {
      throughput: sharedThroughput
    }
    resource: {
      id: databaseName
    }
  }
}

resource visitorCounterContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: visitorCounterDatabase
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        kind: 'Hash'
        paths: [
          '/id'
        ]
        version: 2
      }
    }
  }
}

output cosmosAccountId string = cosmosAccount.id
output cosmosAccountName string = cosmosAccount.name
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output cosmosDatabaseName string = visitorCounterDatabase.name
output cosmosContainerName string = visitorCounterContainer.name
