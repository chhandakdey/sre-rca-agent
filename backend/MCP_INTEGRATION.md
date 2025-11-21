# Model Context Protocol (MCP) Integration

This document describes the Model Context Protocol (MCP) integration in the SRE RCA Agent system.

## Overview

The system now uses **Model Context Protocol (MCP)** to interact with external services (GitHub and Azure) instead of direct SDK/API calls. This provides:

- **Standardized interface** for all external service interactions
- **Flexible deployment** - can use embedded API calls or external MCP servers
- **Better abstraction** - easier to test, mock, and maintain
- **Future-proof** - easy to swap implementations or add new providers

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SRE RCA Agent                            │
│                                                              │
│  ┌────────────┐         ┌──────────────┐                   │
│  │  Agents    │         │ Orchestrator │                   │
│  └─────┬──────┘         └──────┬───────┘                   │
│        │                       │                            │
│        └───────────┬───────────┘                            │
│                    │                                         │
│        ┌───────────▼────────────┐                           │
│        │  MCP Integration Layer │                           │
│        └───────────┬────────────┘                           │
│                    │                                         │
│         ┌──────────┴──────────┐                             │
│         │                     │                             │
│  ┌──────▼──────┐      ┌──────▼───────┐                     │
│  │ GitHub MCP  │      │  Azure MCP   │                     │
│  └──────┬──────┘      └──────┬───────┘                     │
└─────────┼────────────────────┼─────────────────────────────┘
          │                    │
          │ (if external       │ (if external
          │  MCP configured)   │  MCP configured)
          │                    │
   ┌──────▼──────┐      ┌──────▼───────┐
   │   GitHub    │      │    Azure     │
   │ MCP Server  │      │  MCP Server  │
   │ (optional)  │      │  (optional)  │
   └──────┬──────┘      └──────┬───────┘
          │                    │
          │                    │
   ┌──────▼──────┐      ┌──────▼───────┐
   │  GitHub     │      │    Azure     │
   │  REST API   │      │  REST APIs   │
   └─────────────┘      └──────────────┘
```

## Components

### 1. GitHub MCP Integration (`integrations/github_mcp.py`)

**Main Function:**
```python
async def fetch_recent_commits(
    repository: str,
    branch: str = "main",
    since: Optional[datetime] = None,
    service_filter: Optional[str] = None,
    max_commits: int = 50
) -> List[CommitInfo]
```

**MCP Methods:**
- `call_github_mcp("list_commits", params)` - List repository commits
- `call_github_mcp("get_commit", params)` - Get detailed commit information

**Fallback:** If no external MCP server is configured, it directly calls GitHub REST API using httpx.

### 2. Azure MCP Integration (`integrations/azure_mcp.py`)

**Main Functions:**
```python
async def check_deployments(...) -> List[DeploymentInfo]
async def query_app_insights_logs(...) -> List[LogEntry]
```

**MCP Methods:**
- `call_azure_mcp("devops.list_builds", params)` - Azure DevOps pipeline builds
- `call_azure_mcp("appinsights.query", params)` - Application Insights KQL queries

**Fallback:** If no external MCP server is configured, it directly calls Azure REST APIs.

## Configuration

### Environment Variables

```bash
# Optional: External MCP Server URLs
AZURE_MCP_SERVER_URL=http://localhost:3001
GITHUB_MCP_SERVER_URL=http://localhost:3002
```

### Deployment Modes

#### Mode 1: Embedded MCP (Default)
No external MCP servers needed. The integration layer makes direct REST API calls using httpx.

**Pros:**
- Simple deployment
- No additional services needed
- Lower latency

**Cons:**
- Tightly coupled to specific APIs
- Harder to mock for testing

#### Mode 2: External MCP Servers
Configure external MCP server URLs. The system communicates via JSON-RPC 2.0.

**Pros:**
- Better separation of concerns
- Easier to test and mock
- Can share MCP servers across multiple applications
- Centralized credential management

**Cons:**
- Additional deployment complexity
- Network latency
- Need to manage MCP server lifecycle

## MCP Protocol

Communication follows JSON-RPC 2.0 standard:

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "github.list_commits",
  "params": {
    "owner": "myorg",
    "repo": "myrepo",
    "sha": "main",
    "since": "2025-11-21T00:00:00Z",
    "per_page": 50
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": [
    {
      "sha": "abc123...",
      "commit": {
        "message": "Fix payment bug",
        "author": {
          "name": "John Doe",
          "email": "john@example.com",
          "date": "2025-11-21T10:00:00Z"
        }
      },
      "html_url": "https://github.com/..."
    }
  ]
}
```

## Migration from Direct APIs

### What Changed

1. **Removed dependencies:**
   - ❌ `PyGithub` - Direct GitHub SDK
   - ❌ `azure-devops` - Direct Azure DevOps SDK

2. **Added dependencies:**
   - ✅ `httpx` - Async HTTP client for MCP calls

3. **Function signatures:**
   - All integration functions are now `async`
   - Example: `fetch_recent_commits()` → `async def fetch_recent_commits()`

4. **Agent updates:**
   - All agent calls to integration functions now use `await`
   - Example: `commits = await fetch_recent_commits(...)`

### Benefits

✅ **Consistency:** All external calls follow same MCP pattern
✅ **Flexibility:** Easy to switch between embedded and external MCP
✅ **Testability:** Can mock MCP layer for unit tests
✅ **Scalability:** Can deploy MCP servers separately for better resource management
✅ **Security:** Centralize credential management in MCP servers

## Testing

### Unit Tests with Mock MCP

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_fetch_commits_with_mock_mcp():
    mock_response = [{
        "sha": "abc123",
        "commit": {"message": "Test commit"}
    }]
    
    with patch('integrations.github_mcp.call_github_mcp', 
               new=AsyncMock(return_value=mock_response)):
        commits = await fetch_recent_commits(
            repository="test/repo",
            branch="main"
        )
        
        assert len(commits) == 1
        assert commits[0].sha == "abc123"
```

## Future Enhancements

1. **Add more MCP methods:**
   - GitHub: Issues, Pull Requests, Releases
   - Azure: Metrics, Alerts, Resource Graph

2. **MCP Server Implementation:**
   - Create standalone MCP server applications
   - Implement caching layer in MCP servers
   - Add rate limiting and request queuing

3. **Advanced Features:**
   - MCP request tracing and logging
   - Circuit breaker pattern for MCP calls
   - Automatic retry with exponential backoff

## Troubleshooting

### Issue: "MCP Error: connection refused"
**Solution:** Check if external MCP server URL is correct or switch to embedded mode by removing MCP server URL from config.

### Issue: "Unsupported GitHub MCP method"
**Solution:** The method is not implemented in the fallback API layer. Either use an external MCP server or implement the method in `_github_api_call()`.

### Issue: Async/await errors
**Solution:** Ensure all calls to MCP functions use `await` and the calling function is marked as `async`.

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [Azure REST API Documentation](https://learn.microsoft.com/en-us/rest/api/azure/)
