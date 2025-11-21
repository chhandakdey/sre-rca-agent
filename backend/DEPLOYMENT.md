# Setup and Deployment Guide

## Quick Start (Development)

### 1. Install Python Dependencies

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```powershell
# Copy template
copy .env.example .env

# Edit .env with your credentials
notepad .env
```

### 3. Run the Service

```powershell
# Development mode
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the Service

```powershell
# Open another terminal
curl http://localhost:8000/health

# Or open browser
start http://localhost:8000/docs
```

## Production Deployment

### Option 1: Docker Container

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```powershell
docker build -t sre-rca-agent .
docker run -p 8000:8000 --env-file .env sre-rca-agent
```

### Option 2: Azure Container Apps

```powershell
# Login to Azure
az login

# Create resource group
az group create --name rg-rca-agent --location eastus

# Create container app environment
az containerapp env create `
  --name env-rca-agent `
  --resource-group rg-rca-agent `
  --location eastus

# Deploy container app
az containerapp create `
  --name app-rca-agent `
  --resource-group rg-rca-agent `
  --environment env-rca-agent `
  --image your-registry.azurecr.io/sre-rca-agent:latest `
  --target-port 8000 `
  --ingress external `
  --env-vars @env-vars.json
```

### Option 3: Azure App Service

```powershell
# Create App Service plan
az appservice plan create `
  --name plan-rca-agent `
  --resource-group rg-rca-agent `
  --is-linux `
  --sku B1

# Create web app
az webapp create `
  --name app-rca-agent-unique `
  --resource-group rg-rca-agent `
  --plan plan-rca-agent `
  --runtime "PYTHON:3.11"

# Configure environment variables
az webapp config appsettings set `
  --name app-rca-agent-unique `
  --resource-group rg-rca-agent `
  --settings @appsettings.json

# Deploy code
az webapp up `
  --name app-rca-agent-unique `
  --resource-group rg-rca-agent
```

## Azure OpenAI Setup

### 1. Create Azure OpenAI Resource

```powershell
az cognitiveservices account create `
  --name openai-rca-agent `
  --resource-group rg-rca-agent `
  --kind OpenAI `
  --sku S0 `
  --location eastus
```

### 2. Deploy GPT-4.1 Nano Model

```powershell
az cognitiveservices account deployment create `
  --name openai-rca-agent `
  --resource-group rg-rca-agent `
  --deployment-name gpt-4-1-nano `
  --model-name gpt-4 `
  --model-version "0125-preview" `
  --model-format OpenAI `
  --sku-capacity 10 `
  --sku-name "Standard"
```

### 3. Get Credentials

```powershell
# Get endpoint
az cognitiveservices account show `
  --name openai-rca-agent `
  --resource-group rg-rca-agent `
  --query "properties.endpoint" -o tsv

# Get key
az cognitiveservices account keys list `
  --name openai-rca-agent `
  --resource-group rg-rca-agent `
  --query "key1" -o tsv
```

## Azure DevOps Setup

### 1. Create Personal Access Token (PAT)

1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Create new token with scopes:
   - Build: Read
   - Release: Read
   - Code: Read

### 2. Configure in .env

```ini
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_PAT=your-pat-token
```

## GitHub Setup

### 1. Create GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Create new token with scopes:
   - `repo` (all)
   - `read:org`

### 2. Configure in .env

```ini
GITHUB_TOKEN=ghp_your_token_here
GITHUB_ORG=your-org
GITHUB_REPO=your-repo
```

## App Insights Setup

### 1. Create App Insights Workspace

```powershell
az monitor log-analytics workspace create `
  --resource-group rg-rca-agent `
  --workspace-name workspace-rca-agent `
  --location eastus
```

### 2. Get Workspace ID

```powershell
az monitor log-analytics workspace show `
  --resource-group rg-rca-agent `
  --workspace-name workspace-rca-agent `
  --query "customerId" -o tsv
```

## Teams Bot Integration

### 1. Register Bot in Azure

```powershell
az bot create `
  --name bot-rca-agent `
  --resource-group rg-rca-agent `
  --kind registration `
  --sku F0 `
  --endpoint "https://your-app.azurecontainerapps.io/api/v1/teams-webhook"
```

### 2. Configure Teams Channel

1. Go to Azure Portal → Bot resource
2. Add Teams channel
3. Configure messaging endpoint
4. Install bot in Teams

### 3. Update Bot Code

The `/api/v1/teams-webhook` endpoint in `main.py` handles Teams messages.
Extend with Bot Framework SDK for production:

```powershell
pip install botbuilder-core botframework-connector
```

## Monitoring and Logging

### Enable Application Insights

```powershell
# Create Application Insights
az monitor app-insights component create `
  --app app-insights-rca `
  --location eastus `
  --resource-group rg-rca-agent `
  --workspace workspace-rca-agent

# Get instrumentation key
az monitor app-insights component show `
  --app app-insights-rca `
  --resource-group rg-rca-agent `
  --query "instrumentationKey" -o tsv
```

### Add to Code

```python
# In main.py
from opencensus.ext.azure.log_exporter import AzureLogHandler

logger.addHandler(AzureLogHandler(
    connection_string=f'InstrumentationKey={instrumentation_key}'
))
```

## Security Best Practices

### 1. Use Azure Key Vault

```powershell
# Create Key Vault
az keyvault create `
  --name kv-rca-agent `
  --resource-group rg-rca-agent `
  --location eastus

# Store secrets
az keyvault secret set --vault-name kv-rca-agent --name "OpenAI-Key" --value "your-key"
az keyvault secret set --vault-name kv-rca-agent --name "GitHub-Token" --value "your-token"
```

### 2. Update config.py

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://kv-rca-agent.vault.azure.net/", credential=credential)

azure_openai_api_key = client.get_secret("OpenAI-Key").value
github_token = client.get_secret("GitHub-Token").value
```

### 3. Enable Managed Identity

```powershell
# Enable for Container App
az containerapp identity assign `
  --name app-rca-agent `
  --resource-group rg-rca-agent `
  --system-assigned

# Grant Key Vault access
az keyvault set-policy `
  --name kv-rca-agent `
  --object-id <identity-principal-id> `
  --secret-permissions get list
```

## Performance Optimization

### 1. Enable Caching

Add Redis for caching:

```powershell
pip install redis
```

```python
# In config.py
REDIS_URL = "redis://your-redis:6379"
```

### 2. Add Rate Limiting

```powershell
pip install slowapi
```

```python
# In main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/investigate")
@limiter.limit("10/minute")
async def investigate_incident(...):
    ...
```

## Troubleshooting

### Common Issues

**Issue**: Import errors
```powershell
# Solution
pip install --upgrade -r requirements.txt
```

**Issue**: Azure authentication fails
```powershell
# Solution
az login
az account set --subscription <subscription-id>
```

**Issue**: Slow response times
```powershell
# Solution: Check correlation time window
# Edit .env
CORRELATION_TIME_WINDOW_HOURS=12  # Reduce from 24
```

## Maintenance

### Update Dependencies

```powershell
pip list --outdated
pip install --upgrade package-name
pip freeze > requirements.txt
```

### Backup Configuration

```powershell
# Export Key Vault secrets
az keyvault secret backup --vault-name kv-rca-agent --name "OpenAI-Key" --file openai-key.backup
```

### Monitor Health

```powershell
# Check service health
curl http://your-app/health

# View logs
az containerapp logs show `
  --name app-rca-agent `
  --resource-group rg-rca-agent `
  --follow
```

## Scaling

### Horizontal Scaling

```powershell
# Scale Container App
az containerapp update `
  --name app-rca-agent `
  --resource-group rg-rca-agent `
  --min-replicas 2 `
  --max-replicas 10
```

### Vertical Scaling

```powershell
# Increase resources
az containerapp update `
  --name app-rca-agent `
  --resource-group rg-rca-agent `
  --cpu 2.0 `
  --memory 4.0Gi
```
