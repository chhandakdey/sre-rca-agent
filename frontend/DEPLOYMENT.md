# SRE RCA Teams Bot - Deployment Guide

This guide covers deploying the Python-based Teams bot to various environments.

## 🎯 Deployment Options

1. **Azure App Service** (Recommended for production)
2. **Azure Container Instances**
3. **Azure Kubernetes Service (AKS)**
4. **On-premises Server**

---

## 📦 Azure App Service Deployment

### Prerequisites

- Azure CLI installed
- Azure subscription
- Bot registered in Azure Bot Service

### Step 1: Prepare for Deployment

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "your-subscription-id"

# Create resource group (if not exists)
az group create --name rca-bot-rg --location eastus
```

### Step 2: Create App Service

```bash
# Create App Service Plan
az appservice plan create \
  --name rca-bot-plan \
  --resource-group rca-bot-rg \
  --sku B1 \
  --is-linux

# Create Web App with Python runtime
az webapp create \
  --name sre-rca-teams-bot \
  --resource-group rca-bot-rg \
  --plan rca-bot-plan \
  --runtime "PYTHON|3.11"
```

### Step 3: Configure Environment Variables

```bash
az webapp config appsettings set \
  --name sre-rca-teams-bot \
  --resource-group rca-bot-rg \
  --settings \
    BOT_ID="your-bot-id" \
    BOT_PASSWORD="your-bot-password" \
    BACKEND_API_URL="https://your-backend-api.azurewebsites.net" \
    BACKEND_API_TIMEOUT="30000"
```

### Step 4: Deploy Code

```bash
# From the frontend directory
cd frontend

# Create deployment package (zip without venv)
zip -r deploy.zip src/ requirements.txt config/ .env

# Deploy to Azure
az webapp deployment source config-zip \
  --name sre-rca-teams-bot \
  --resource-group rca-bot-rg \
  --src deploy.zip

# Set startup command
az webapp config set \
  --name sre-rca-teams-bot \
  --resource-group rca-bot-rg \
  --startup-file "python src/app.py"
```

### Step 5: Update Bot Messaging Endpoint

Update your Azure Bot's messaging endpoint to:
```
https://sre-rca-teams-bot.azurewebsites.net/api/messages
```

---

## 🐳 Docker Deployment

### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY config/ ./config/

# Expose port
EXPOSE 3978

# Start application
CMD ["python", "src/app.py"]
```

### Build and Run

```bash
# Build image
docker build -t sre-rca-teams-bot:latest .

# Run container
docker run -d \
  --name sre-bot \
  -p 3978:3978 \
  -e BOT_ID="your-bot-id" \
  -e BOT_PASSWORD="your-bot-password" \
  -e BACKEND_API_URL="http://backend:8000" \
  sre-rca-teams-bot:latest
```

### Deploy to Azure Container Registry

```bash
# Create ACR
az acr create \
  --name rcabotacr \
  --resource-group rca-bot-rg \
  --sku Basic

# Login to ACR
az acr login --name rcabotacr

# Tag and push image
docker tag sre-rca-teams-bot:latest rcabotacr.azurecr.io/sre-bot:latest
docker push rcabotacr.azurecr.io/sre-bot:latest

# Deploy to Container Instance
az container create \
  --name sre-rca-bot \
  --resource-group rca-bot-rg \
  --image rcabotacr.azurecr.io/sre-bot:latest \
  --dns-name-label sre-rca-bot \
  --ports 3978 \
  --environment-variables \
    BOT_ID="your-bot-id" \
    BOT_PASSWORD="your-bot-password" \
    BACKEND_API_URL="https://your-backend.com"
```

---

## ☸️ Kubernetes Deployment

### Create Kubernetes Manifests

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sre-rca-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sre-rca-bot
  template:
    metadata:
      labels:
        app: sre-rca-bot
    spec:
      containers:
      - name: bot
        image: rcabotacr.azurecr.io/sre-bot:latest
        ports:
        - containerPort: 3978
        env:
        - name: BOT_ID
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: bot-id
        - name: BOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: bot-password
        - name: BACKEND_API_URL
          value: "http://backend-service:8000"
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: sre-rca-bot-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 3978
  selector:
    app: sre-rca-bot
```

**secret.yaml:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: bot-secrets
type: Opaque
stringData:
  bot-id: "your-bot-id"
  bot-password: "your-bot-password"
```

### Deploy to AKS

```bash
# Create AKS cluster (if needed)
az aks create \
  --name rca-bot-cluster \
  --resource-group rca-bot-rg \
  --node-count 2 \
  --generate-ssh-keys

# Get credentials
az aks get-credentials \
  --name rca-bot-cluster \
  --resource-group rca-bot-rg

# Apply manifests
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Get external IP
kubectl get service sre-rca-bot-service
```

---

## 🔒 Security Configuration

### Use Azure Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name rca-bot-kv \
  --resource-group rca-bot-rg \
  --location eastus

# Add secrets
az keyvault secret set --vault-name rca-bot-kv --name BotId --value "your-bot-id"
az keyvault secret set --vault-name rca-bot-kv --name BotPassword --value "your-bot-password"

# Configure App Service to use Key Vault
az webapp identity assign \
  --name sre-rca-teams-bot \
  --resource-group rca-bot-rg

# Grant access
az keyvault set-policy \
  --name rca-bot-kv \
  --object-id <managed-identity-object-id> \
  --secret-permissions get list
```

Update your code to use Azure Key Vault:
```javascript
const { SecretClient } = require("@azure/keyvault-secrets");
const { DefaultAzureCredential } = require("@azure/identity");

const credential = new DefaultAzureCredential();
const client = new SecretClient("https://rca-bot-kv.vault.azure.net/", credential);

const botId = await client.getSecret("BotId");
const botPassword = await client.getSecret("BotPassword");
```

---

## 📊 Monitoring and Logging

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app rca-bot-insights \
  --location eastus \
  --resource-group rca-bot-rg

# Get instrumentation key
az monitor app-insights component show \
  --app rca-bot-insights \
  --resource-group rca-bot-rg \
  --query instrumentationKey

# Add to app settings
az webapp config appsettings set \
  --name sre-rca-teams-bot \
  --resource-group rca-bot-rg \
  --settings APPINSIGHTS_INSTRUMENTATION_KEY="your-key"
```

Add to your code:
```javascript
const appInsights = require('applicationinsights');
appInsights.setup(process.env.APPINSIGHTS_INSTRUMENTATION_KEY)
  .setAutoCollectRequests(true)
  .setAutoCollectPerformance(true)
  .setAutoCollectExceptions(true)
  .start();
```

---

## 🧪 Health Checks

Configure health checks for your deployment:

```bash
az webapp config set \
  --name sre-rca-teams-bot \
  --resource-group rca-bot-rg \
  --health-check-path "/health"
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd frontend
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        cd frontend
        pytest
    
    - name: Deploy to Azure
      uses: azure/webapps-deploy@v2
      with:
        app-name: 'sre-rca-teams-bot'
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
        package: frontend
```

---

## 📋 Post-Deployment Checklist

- [ ] Verify bot responds at messaging endpoint
- [ ] Test health check endpoint
- [ ] Confirm backend connectivity
- [ ] Upload Teams app package
- [ ] Test bot in Teams
- [ ] Configure monitoring alerts
- [ ] Document production URLs
- [ ] Set up backup/disaster recovery
- [ ] Review security settings
- [ ] Enable logging and monitoring

---

## 🆘 Troubleshooting

### Bot not reachable
- Check App Service logs: `az webapp log tail --name sre-rca-teams-bot --resource-group rca-bot-rg`
- Verify networking rules and firewall settings
- Test endpoint directly with curl

### Performance issues
- Scale up App Service plan
- Enable Application Insights
- Check backend response times
- Review resource utilization

### Authentication failures
- Verify Bot ID and Password
- Check Azure Bot configuration
- Review Azure AD permissions

---

## 📚 Additional Resources

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure Bot Service Documentation](https://docs.microsoft.com/azure/bot-service/)
- [Azure Key Vault Documentation](https://docs.microsoft.com/azure/key-vault/)
