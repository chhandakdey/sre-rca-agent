# Azure MCP Integration - Updated Implementation

This document describes the updated Azure MCP (Model Context Protocol) integration that uses the stdio client approach for better connectivity and session management.

## Overview

The Azure MCP integration has been updated to use the modern MCP client pattern with:
- **Stdio Client Transport**: Uses `stdio_client` for robust MCP server communication
- **Session Management**: Persistent session with proper initialization and cleanup
- **Tool Caching**: Available tools are cached for efficient reuse
- **Azure OpenAI Integration**: Seamless integration with Azure OpenAI for conversational AI

## Architecture

```
┌─────────────────────┐
│  Your Application   │
│   (Python code)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  azure_mcp.py       │
│  - Session Mgmt     │
│  - Tool Calls       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  MCP Client         │
│  (stdio_client)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  @azure/mcp         │
│  (NPX Server)       │
└─────────────────────┘
```

## Key Components

### 1. Session Management

```python
from integrations.azure_mcp import (
    initialize_azure_mcp,
    get_azure_mcp_session,
    close_azure_mcp
)

# Initialize (first time)
session = await initialize_azure_mcp()

# Get existing session
session = await get_azure_mcp_session()

# Cleanup
await close_azure_mcp()
```

### 2. Tool Calling

```python
from integrations.azure_mcp import call_azure_mcp_tool

# Call an Azure MCP tool
result = await call_azure_mcp_tool(
    "azure_resources-query_azure_resource_graph",
    {
        "arg_intent": "list all app services in subscription",
        "useDefaultSubscriptionFilter": True
    }
)
```

### 3. Conversational AI with Azure OpenAI

```python
from openai import AzureOpenAI
from integrations.azure_mcp import initialize_azure_mcp, call_azure_mcp_tool, _available_tools

# Initialize clients
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
    api_key=AZURE_OPENAI_API_KEY
)

await initialize_azure_mcp()

# Chat loop
messages = [{"role": "user", "content": "What Azure resources do I have?"}]

response = client.chat.completions.create(
    model=AZURE_OPENAI_MODEL,
    messages=messages,
    tools=_available_tools
)

# Handle tool calls
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        result = await call_azure_mcp_tool(
            tool_call.function.name,
            json.loads(tool_call.function.arguments)
        )
        # Add result to messages and continue...
```

## Changes from Previous Implementation

| Aspect | Before | After |
|--------|--------|-------|
| **Transport** | HTTP/JSON-RPC | stdio client |
| **Connection** | Per-request | Persistent session |
| **Tool Discovery** | Manual mapping | Automatic from MCP |
| **Session State** | Stateless | Stateful with caching |
| **Error Handling** | Basic | Comprehensive with fallback |
| **Logging** | print statements | Structured logging |

## Installation

### Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Node.js and NPM** (for @azure/mcp):
   ```bash
   # The MCP server is automatically installed via npx
   # No manual installation needed
   ```

### Environment Variables

Update your `.env` file:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_MODEL=gpt-4

# Azure MCP
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id

# App Insights
APP_INSIGHTS_WORKSPACE_ID=your-workspace-id
APP_INSIGHTS_APP_ID=your-app-id
```

## Usage Examples

### Example 1: Test Connection

```bash
cd backend
python test_azure_mcp_connection.py
```

This will:
- Initialize the MCP session
- List all available tools
- Run a test query
- Display results

### Example 2: Interactive Mode

```bash
cd backend
python test_azure_mcp_connection.py --interactive
```

Allows you to:
- Select tools by number or name
- Provide custom parameters
- See real-time results

### Example 3: Conversational Agent

```bash
cd backend
python azure_mcp_conversation_example.py
```

Starts a conversational agent where you can:
- Ask questions about Azure resources
- Get AI-powered responses
- Execute Azure queries automatically

### Example 4: Quick Test

```bash
cd backend
python azure_mcp_conversation_example.py --quick
```

Runs a single test query to verify everything works.

## Available Azure MCP Tools

The Azure MCP server provides numerous tools, including:

- `azure_resources-query_azure_resource_graph` - Query Azure Resource Graph
- `azure_development-recommend_custom_modes` - Get Azure development recommendations
- `mcp_azure_mcp_get_bestpractices` - Get Azure best practices
- `mcp_azure_mcp_deploy` - Azure deployment operations
- `mcp_azure_mcp_azd` - Azure Developer CLI operations
- And many more...

Use `test_azure_mcp_connection.py` to see the full list of available tools.

## Integration with Existing Code

The updated implementation is backward compatible. Existing code using `call_azure_mcp()` will continue to work:

```python
# Old code still works
result = await call_azure_mcp(
    "appinsights.query",
    {
        "app_id": workspace_id,
        "query": kql_query,
        "max_results": max_results
    }
)
```

However, the new approach is recommended:

```python
# New recommended approach
result = await call_azure_mcp_tool(
    "azure_resources-query_azure_resource_graph",
    {
        "arg_intent": "your natural language query",
        "useDefaultSubscriptionFilter": True
    }
)
```

## Troubleshooting

### Issue: "Import mcp could not be resolved"

**Solution**: Install the MCP package:
```bash
pip install mcp>=1.0.0
```

### Issue: "npx command not found"

**Solution**: Install Node.js and NPM:
- Download from: https://nodejs.org/
- Or use package manager: `winget install OpenJS.NodeJS`

### Issue: Session initialization fails

**Solution**: Check environment variables and Azure credentials:
```bash
# Test Azure credentials
az login
az account show
```

### Issue: Tool calls failing

**Solution**: 
1. Verify Azure subscription access
2. Check resource permissions
3. Review logs in `test_azure_mcp_connection.py`

## Performance Considerations

- **Session Reuse**: Session is initialized once and reused
- **Tool Caching**: Available tools are cached on initialization
- **Async Operations**: All operations are async for better concurrency
- **Connection Pooling**: MCP client maintains persistent connection

## Security

- Never commit `.env` files with credentials
- Use Azure Managed Identity in production
- Rotate keys regularly
- Follow principle of least privilege for Azure access

## Best Practices

1. **Initialize Once**: Initialize the MCP session once at application startup
2. **Cleanup Properly**: Always call `close_azure_mcp()` on shutdown
3. **Error Handling**: Wrap tool calls in try-except blocks
4. **Logging**: Use structured logging for better debugging
5. **Async/Await**: Always use async functions for MCP operations

## Contributing

When adding new Azure MCP functionality:

1. Add new tool mappings to `call_azure_mcp()` if needed
2. Update documentation with examples
3. Add tests to `test_azure_mcp_connection.py`
4. Follow existing error handling patterns
5. Use structured logging

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Azure MCP Server](https://www.npmjs.com/package/@azure/mcp)
- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure Resource Graph](https://learn.microsoft.com/en-us/azure/governance/resource-graph/)

## License

Same as parent project.
