param location string = resourceGroup().location
param namePrefix string = 'canadaca'

// Container Registry
resource acr 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: '${namePrefix}acr${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// Log Analytics
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${namePrefix}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Container Apps Environment
resource env 'Microsoft.App/managedEnvironments@2022-11-01-preview' = {
  name: '${namePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Web App (Hosting the Chatbot)
resource webApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${namePrefix}-web'
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
      }
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
      ]
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.name
          passwordSecretRef: 'acr-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'main'
          image: '${acr.properties.loginServer}/canadaca-chat:latest'
          resources: {
            cpu: 0.5
            memory: '1.0Gi'
          }
          env: [
            { name: 'PORT', value: '8000' }
            { name: 'ENVIRONMENT', value: 'production' }
            // Note: Add DATABASE_URL, REDIS_URL, AWS credentials here via secrets
          ]
        }
      ]
      scale: {
        minReplicas: 0 // Scales to 0 to save money if idle!
        maxReplicas: 5
      }
    }
  }
}

// Scheduled Job (Hosting the Scraper)
resource scraperJob 'Microsoft.App/jobs@2023-05-01' = {
  name: '${namePrefix}-scraper'
  location: location
  properties: {
    environmentId: env.id
    configuration: {
      triggerType: 'Schedule'
      scheduleTriggerConfig: {
        cronExpression: '0 3 * * *' // 3 AM UTC every day
        parallelism: 1
        replicaCompletionCount: 1
      }
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
      ]
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.name
          passwordSecretRef: 'acr-password'
        }
      ]
      replicaTimeout: 3600 // 1 hour timeout
      replicaRetryLimit: 1
    }
    template: {
      containers: [
        {
          name: 'scraper'
          image: '${acr.properties.loginServer}/canadaca-chat:latest'
          command: ['python', 'scripts/incremental_ingest.py', '--filter', 'en/revenue-agency/services/tax/businesses/']
          resources: {
            cpu: 0.5
            memory: '1.0Gi'
          }
          env: [
             { name: 'ENVIRONMENT', value: 'production' }
             // Note: Add DATABASE_URL, REDIS_URL, AWS credentials here via secrets
          ]
        }
      ]
    }
  }
}

output acrLoginServer string = acr.properties.loginServer
output webUrl string = webApp.properties.configuration.ingress.fqdn
