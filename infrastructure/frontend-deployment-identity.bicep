targetScope = 'resourceGroup'

@description('Azure region for the user-assigned managed identity.')
param location string

@description('Name of the frontend GitHub Actions deployment identity.')
param identityName string

@description('GitHub Actions OIDC subject permitted to use this identity.')
param githubOidcSubject string

resource frontendDeploymentIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource githubMainCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2024-11-30' = if (!empty(githubOidcSubject)) {
  parent: frontendDeploymentIdentity
  name: 'github-main'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    audiences: [
      'api://AzureADTokenExchange'
    ]
    subject: githubOidcSubject
  }
}

output clientId string = frontendDeploymentIdentity.properties.clientId
output principalId string = frontendDeploymentIdentity.properties.principalId
