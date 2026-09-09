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

output resourceGroupId string = resourceGroup.id
output resourceGroupName string = resourceGroup.name
output resourceGroupLocation string = resourceGroup.location
