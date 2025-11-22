# Deployment Correlation Window - Environment Variable Update

## Summary

Updated the deployment correlation feature to use a configurable environment variable instead of hardcoded values.

## Changes Made

### 1. Configuration (`backend/config.py`)
Added new setting:
```python
# Deployment Correlation Settings
deployment_correlation_hours: int = 2
```

**Environment Variable:** `DEPLOYMENT_CORRELATION_HOURS`  
**Default Value:** 2 hours

### 2. GitHub MCP Integration (`backend/integrations/github_mcp.py`)

Updated `fetch_recent_deployments()` function:

**New Parameter:**
- `incident_time: Optional[datetime] = None` - When provided, automatically calculates the lookback window using `DEPLOYMENT_CORRELATION_HOURS`

**Behavior:**
1. If `since` parameter is provided → Use it directly (explicit override)
2. If `incident_time` is provided and `since` is None → Calculate: `since = incident_time - timedelta(hours=DEPLOYMENT_CORRELATION_HOURS)`
3. If neither provided → Use general correlation window as fallback

**Usage Examples:**

```python
# Recommended: Use incident_time parameter
deployments = await fetch_recent_deployments(
    repository="org/repo",
    incident_time=incident_datetime,  # Automatically uses env variable
    environment="production"
)

# Alternative: Explicit since parameter
deployments = await fetch_recent_deployments(
    repository="org/repo",
    since=datetime.now() - timedelta(hours=2),
    environment="production"
)
```

### 3. Test Updates (`backend/test_deployment_correlation.py`)

- Updated to use `incident_time` parameter instead of calculating `since` manually
- Added import for `settings` from `config`
- Added logging to show the configured correlation window
- Updated documentation in the integration pattern demonstration

### 4. Documentation (`backend/ENV_VARIABLES.md`)

Created comprehensive documentation covering:
- Environment variable description and defaults
- Usage examples
- Best practices for different deployment frequencies
- Configuration examples
- Testing instructions

## Benefits

✅ **Configurable:** Easily adjust correlation window without code changes  
✅ **Flexible:** Supports both `incident_time` (automatic) and `since` (explicit) parameters  
✅ **Documented:** Clear configuration guide and best practices  
✅ **Backward Compatible:** Existing code using `since` parameter continues to work  
✅ **Environment-Aware:** Different settings for dev/staging/production environments  

## Configuration

Add to `.env` file:

```bash
# Default: 2 hours
DEPLOYMENT_CORRELATION_HOURS=2

# For frequent deployments
DEPLOYMENT_CORRELATION_HOURS=1

# For comprehensive analysis
DEPLOYMENT_CORRELATION_HOURS=6
```

## Testing

```bash
# Run correlation test
..\venv\Scripts\Activate.ps1
python test_deployment_correlation.py
```

Expected output:
```
⏱️ Correlation Window: 2 hours (from DEPLOYMENT_CORRELATION_HOURS)
[GitHub MCP] Using deployment correlation window of 2 hours from incident time
```

## Next Steps

Consider adding to the main `.env.example` file:
```bash
# Deployment correlation settings
DEPLOYMENT_CORRELATION_HOURS=2  # Hours to look back for deployment correlation
```
