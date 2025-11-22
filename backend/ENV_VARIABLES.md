# Environment Variables Configuration

This document describes the configurable environment variables for the SRE RCA Agent.

## Deployment Correlation Settings

### `DEPLOYMENT_CORRELATION_HOURS`

**Type:** Integer  
**Default:** `2`  
**Description:** Time window (in hours) to look back from an incident time when fetching related deployments.

This setting controls how far back the system should search for deployments that might be correlated with an incident. For example:
- If an incident occurred at 10:30 AM
- With `DEPLOYMENT_CORRELATION_HOURS=2`
- The system will fetch deployments from 8:30 AM to 10:30 AM

**Usage in code:**
```python
from integrations.github_mcp import fetch_recent_deployments
from datetime import datetime

# Automatically uses DEPLOYMENT_CORRELATION_HOURS
deployments = await fetch_recent_deployments(
    repository="org/repo",
    incident_time=incident_datetime,  # System looks back N hours from this time
    environment="production"
)
```

**Configuration examples:**

```bash
# .env file

# Default - look back 2 hours
DEPLOYMENT_CORRELATION_HOURS=2

# For systems with frequent deployments - narrow window
DEPLOYMENT_CORRELATION_HOURS=1

# For systems with infrequent deployments - wider window
DEPLOYMENT_CORRELATION_HOURS=6

# For comprehensive analysis
DEPLOYMENT_CORRELATION_HOURS=24
```

**Related settings:**
- `CORRELATION_TIME_WINDOW_HOURS=24` - General correlation window for all data sources (logs, metrics, etc.)

**Best practices:**
1. **High-frequency deployments** (multiple times per day): Use 1-2 hours
2. **Medium-frequency deployments** (daily): Use 2-4 hours
3. **Low-frequency deployments** (weekly): Use 24-48 hours
4. **Balance performance vs. accuracy**: Larger windows return more results but may include less relevant deployments

## Other Correlation Settings

### `CORRELATION_TIME_WINDOW_HOURS`

**Type:** Integer  
**Default:** `24`  
**Description:** General correlation time window for logs, metrics, and other data sources (hours).

This is the fallback correlation window used when `incident_time` is not provided or for non-deployment data sources.

## Usage Example

```python
# Example .env file configuration
DEPLOYMENT_CORRELATION_HOURS=2
CORRELATION_TIME_WINDOW_HOURS=24

# Azure credentials
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# GitHub credentials
GITHUB_TOKEN=your-github-token
GITHUB_ORG=your-org
GITHUB_REPO=your-repo
```

## Testing Configuration

You can test your configuration with:

```bash
# Activate virtual environment
..\venv\Scripts\Activate.ps1

# Run deployment correlation test
python test_deployment_correlation.py
```

The test will show the configured correlation window in the output:
```
⏱️ Correlation Window: 2 hours (from DEPLOYMENT_CORRELATION_HOURS)
```
