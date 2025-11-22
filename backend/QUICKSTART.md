# Quick Start Guide - Azure MCP Integration

## Prerequisites

1. **Python 3.8+** installed
2. **Node.js 16+** and **npm** installed (for MCP server)
3. **Azure credentials** configured
4. **Environment variables** set up

## Installation Steps

### Step 1: Install Node.js (if not already installed)

**Windows (PowerShell)**:
```powershell
winget install OpenJS.NodeJS
```

**Or download from**: https://nodejs.org/

**Verify installation**:
```bash
node --version   # Should show v16.0.0 or higher
npm --version    # Should show v8.0.0 or higher
```

### Step 2: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `mcp>=1.0.0` - Model Context Protocol client
- All other required packages

### Step 3: Configure Environment Variables

Create or update `.env` file in the `backend` directory:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_MODEL=gpt-4

# Azure MCP Configuration
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id

# Azure DevOps (if using)
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_PAT=your-pat-token

# App Insights (if using)
APP_INSIGHTS_WORKSPACE_ID=your-workspace-id
APP_INSIGHTS_APP_ID=your-app-id
APP_INSIGHTS_CONNECTION_STRING=your-connection-string

# GitHub (if using)
GITHUB_TOKEN=your-github-token
GITHUB_ORG=your-org
GITHUB_REPO=your-repo

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-here
```

### Step 4: Test the Connection

Run the test script:

```bash
cd backend
python test_azure_mcp_connection.py
```

**Expected Output**:
```
============================================================
Testing Azure MCP Connection
============================================================

1. Initializing Azure MCP session...
✓ Session initialized successfully

2. Available Azure MCP Tools (XX):
   1. azure_resources-query_azure_resource_graph
      Query Azure Resource Graph for information about...
   2. azure_development-recommend_custom_modes
      This tool captures user intent about Azure...
   ...

3. Testing Azure Resource Query...
✓ Query executed successfully
   Result preview: {...}

============================================================
Azure MCP Connection Test Complete
============================================================
```

### Step 5: Try Interactive Mode (Optional)

```bash
python test_azure_mcp_connection.py --interactive
```

This allows you to:
- Browse available tools
- Test individual tools
- Provide custom parameters
- See immediate results

### Step 6: Run Conversational Agent (Optional)

```bash
python azure_mcp_conversation_example.py
```

Ask questions like:
- "List my Azure subscriptions"
- "What resources do I have in Azure?"
- "Show me my App Services"

## Troubleshooting

### Issue: "Import mcp could not be resolved"

**Cause**: MCP package not installed

**Fix**:
```bash
pip install mcp>=1.0.0
```

### Issue: "npx: command not found"

**Cause**: Node.js/npm not installed or not in PATH

**Fix**:
1. Install Node.js from https://nodejs.org/
2. Restart terminal/VSCode
3. Verify: `npx --version`

### Issue: "Failed to initialize Azure MCP"

**Possible Causes**:
1. Network connectivity issues
2. Firewall blocking npx
3. Azure credentials not configured

**Fixes**:
```bash
# Test npx can download packages
npx cowsay "test"

# Test Azure login
az login
az account show

# Check environment variables
# Make sure .env file exists and has correct values
```

### Issue: "Azure credentials error"

**Fix**:
```bash
# Login to Azure
az login

# Set default subscription
az account set --subscription "your-subscription-id"

# Verify
az account show
```

### Issue: MCP server takes long to start

**Normal behavior**: First run takes 2-3 seconds as npx downloads @azure/mcp

**Subsequent runs**: Should be faster (package is cached)

## Verification Checklist

✅ Python 3.8+ installed  
✅ Node.js 16+ installed  
✅ npm working  
✅ `.env` file configured  
✅ Azure credentials valid  
✅ `pip install -r requirements.txt` completed  
✅ `test_azure_mcp_connection.py` runs successfully  

## Next Steps

1. **Integrate with your application**:
   ```python
   from integrations.azure_mcp import initialize_azure_mcp, call_azure_mcp_tool
   
   # At application startup
   await initialize_azure_mcp()
   
   # Use in your code
   result = await call_azure_mcp_tool("tool_name", {"param": "value"})
   ```

2. **Add to FastAPI startup**:
   ```python
   @app.on_event("startup")
   async def startup_event():
       await initialize_azure_mcp()
   
   @app.on_event("shutdown")
   async def shutdown_event():
       await close_azure_mcp()
   ```

3. **Read documentation**:
   - `AZURE_MCP_INTEGRATION.md` - Full documentation
   - `AZURE_MCP_UPDATE_SUMMARY.md` - Changes and migration guide

## Getting Help

1. Check logs for error messages
2. Review `AZURE_MCP_INTEGRATION.md` for detailed info
3. Run tests in debug mode:
   ```bash
   python test_azure_mcp_connection.py --interactive
   ```
4. Verify Azure credentials and permissions

## Common Use Cases

### Query Azure Resources
```python
result = await call_azure_mcp_tool(
    "azure_resources-query_azure_resource_graph",
    {
        "arg_intent": "list all app services",
        "useDefaultSubscriptionFilter": True
    }
)
```

### Get Azure Best Practices
```python
result = await call_azure_mcp_tool(
    "mcp_azure_mcp_get_bestpractices",
    {
        "intent": "deploying a web app",
        "command": "get"
    }
)
```

### Azure Development Help
```python
result = await call_azure_mcp_tool(
    "azure_development-recommend_custom_modes",
    {
        "intent": "create a container app"
    }
)
```

## Success!

If all tests pass, your Azure MCP integration is ready to use! 🎉

You can now:
- Query Azure resources programmatically
- Use AI to interact with Azure services
- Build conversational agents for Azure management
- Automate Azure operations with natural language

Happy coding! 🚀
