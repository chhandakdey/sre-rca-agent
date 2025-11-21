# SRE RCA Agent - Root Cause Analysis System

A comprehensive multi-agent system for automated root cause analysis (RCA) using LangChain, Azure OpenAI GPT-4.1 Nano, and integration with Azure MCP and GitHub MCP.

## 🎯 Overview

This FastAPI-based backend service provides intelligent root cause analysis for incidents reported through Microsoft Teams. It uses a sophisticated multi-agent architecture where specialized agents work together to:

1. **Parse incident context** from natural language descriptions
2. **Fetch recent code changes** from GitHub
3. **Check deployment history** from Azure DevOps
4. **Query application logs** from Azure App Insights
5. **Correlate data** using rule-based and ML-based techniques
6. **Generate actionable insights** with recommendations

## 🏗️ Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                        │
│              (Coordinates workflow)                          │
└────────────┬─────────────────────────────────────┬──────────┘
             │                                     │
    ┌────────▼────────┐                   ┌───────▼──────────┐
    │ Context Parser  │                   │ GitHub Fetcher   │
    │  Agent (GPT)    │                   │     Agent        │
    └────────┬────────┘                   └───────┬──────────┘
             │                                     │
    ┌────────▼────────────────────────────────────▼──────────┐
    │              Correlation Engine Agent                   │
    │    (Rule-based + ML + LLM reasoning)                   │
    └────────┬───────────────────────────────────────────────┘
             │
    ┌────────▼────────┐
    │   Response      │
    │   Generator     │
    └─────────────────┘
```

### Individual Agents

1. **Context Parser Agent** (`agents/context_parser.py`)
   - Uses GPT-4.1 Nano via Azure Foundry
   - Extracts: service names, error codes, timestamps, severity, keywords
   - Provides structured context for downstream agents

2. **GitHub Fetcher Agent** (`agents/github_fetcher.py`)
   - Integrates with GitHub MCP
   - Fetches commits within incident time window
   - Filters by service/module names

3. **Azure DevOps Checker** (via tools)
   - Queries Azure DevOps pipelines
   - Tracks deployment status and history
   - Links commits to deployments

4. **App Insights Retriever** (via tools)
   - Executes KQL queries against App Insights
   - Retrieves relevant log entries
   - Filters by time, service, error codes

5. **Correlation Engine Agent** (`agents/correlation_engine.py`)
   - Rule-based: Time proximity, service matching, file relevance
   - ML-based: Anomaly detection using Isolation Forest
   - LLM-enhanced: Deeper reasoning via GPT-4.1 Nano
   - Ranks suspected root causes by confidence

6. **Response Generator Agent** (`agents/response_generator.py`)
   - Generates executive summary
   - Creates timeline of events
   - Provides actionable recommendations
   - Formats Teams Adaptive Cards

## 📁 Project Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management
├── models.py                  # Pydantic data models
├── tools.py                   # LangChain tools
├── orchestrator.py            # Main controller agent
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
│
├── agents/                    # Individual agent implementations
│   ├── __init__.py
│   ├── context_parser.py     # Context Parser Agent
│   ├── github_fetcher.py     # GitHub Fetcher Agent
│   ├── correlation_engine.py # Correlation Engine Agent
│   └── response_generator.py # Response Generator Agent
│
└── integrations/             # External service integrations
    ├── __init__.py
    ├── github_mcp.py         # GitHub MCP integration
    └── azure_mcp.py          # Azure MCP integration
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Azure OpenAI (GPT-4.1 Nano deployment)
- Azure subscription with:
  - Azure DevOps organization
  - App Insights workspace
  - Azure Monitor access
- GitHub account with API token

### 1. Clone and Navigate

```bash
cd backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
```

Edit `.env` with your actual values:

```ini
# Azure OpenAI / Azure Foundry
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-1-nano

# Azure Authentication
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id

# Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_PAT=your-personal-access-token

# App Insights
APP_INSIGHTS_WORKSPACE_ID=your-workspace-id

# GitHub
GITHUB_TOKEN=your-github-token
GITHUB_ORG=your-github-org
GITHUB_REPO=your-github-repo

# Security
SECRET_KEY=generate-a-secure-random-key
```

### 5. Run the Application

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 API Endpoints

### Main RCA Endpoint

**POST** `/api/v1/investigate`

Performs complete root cause analysis.

**Request Body:**
```json
{
  "raw_text": "Users experiencing 500 errors in payment service around 2PM today. Error code: ERR_PAYMENT_GATEWAY_TIMEOUT",
  "user_id": "user@company.com",
  "timestamp": "2025-11-21T14:00:00Z"
}
```

**Response:**
```json
{
  "summary": "Investigation identified a recent deployment as the likely cause...",
  "top_suspects": [
    {
      "cause_description": "Deployment 'payment-service-deploy' to production",
      "confidence_score": 0.87,
      "confidence_level": "high",
      "evidence": [
        "Deployment completed 5 minutes before first error",
        "Commit modified gateway timeout configuration"
      ],
      "reasoning": "Strong temporal correlation and code changes...",
      "related_commits": [...],
      "related_deployments": [...],
      "related_logs": [...]
    }
  ],
  "timeline": [...],
  "recommendations": [
    "Review commit abc123 which modified gateway configuration",
    "Consider rolling back deployment 456"
  ],
  "investigation_metadata": {...},
  "adaptive_card": {...}
}
```

### Testing Endpoints

**POST** `/api/v1/parse-context` - Test context parsing only

**POST** `/api/v1/fetch-commits` - Test GitHub fetching only

**GET** `/api/v1/status/{request_id}` - Check investigation status

### Health Check

**GET** `/health` - Service health check

## 🧪 Testing

### Quick Test

```bash
# Test with curl
curl -X POST "http://localhost:8000/api/v1/investigate" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Payment service is down with 500 errors",
    "user_id": "test@example.com"
  }'
```

### Python Test

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/investigate",
    json={
        "raw_text": "Users seeing timeout errors in checkout service since 3PM",
        "user_id": "sre@company.com",
        "timestamp": "2025-11-21T15:00:00Z"
    }
)

result = response.json()
print(f"Summary: {result['summary']}")
print(f"Top Suspect: {result['top_suspects'][0]['cause_description']}")
```

## 🔧 Configuration Options

### Correlation Settings

```python
# config.py or .env
CORRELATION_TIME_WINDOW_HOURS=24    # How far back to look
CORRELATION_MAX_RESULTS=10          # Max correlation matches
ENABLE_ML_CORRELATION=true          # Enable ML-based anomaly detection
```

### Agent Behavior

Each agent can be configured independently:

- **Context Parser**: Temperature, model deployment
- **Correlation Engine**: Scoring weights, ML thresholds
- **Response Generator**: Summary length, recommendations count

## 🔌 Integration Details

### GitHub MCP Integration

Located in `integrations/github_mcp.py`

**Current Implementation**: Uses PyGithub library

**Production Options**:
1. Use official GitHub MCP client/SDK
2. Call external MCP server via HTTP
3. Direct GitHub API integration

### Azure MCP Integration

Located in `integrations/azure_mcp.py`

**Current Implementation**: Uses Azure SDKs directly

**Components**:
- Azure DevOps: `azure-devops` package
- App Insights: `azure-monitor-query` package
- Authentication: `azure-identity` package

**Production Options**:
1. Use official Azure MCP client/SDK
2. Call external MCP server via HTTP
3. Enhance with Azure Resource Graph queries

## 📊 Data Models

All models are defined in `models.py` using Pydantic:

- `UserContext`: Input from user
- `ParsedContext`: Structured entities
- `CommitInfo`: GitHub commit data
- `DeploymentInfo`: Azure DevOps deployment data
- `LogEntry`: App Insights log entry
- `CorrelationMatch`: Suspected root cause
- `RCAResponse`: Final response

## 🤖 Agent Workflow

1. **User submits incident** → `UserContext`
2. **Context Parser** → `ParsedContext` (service, errors, time, keywords)
3. **Parallel Execution**:
   - GitHub Fetcher → Recent commits
   - DevOps Checker → Recent deployments
   - App Insights → Relevant logs
4. **Correlation Engine** → Analyzes all data
5. **Response Generator** → Final response with Adaptive Card

## 📈 Correlation Logic

### Rule-Based Scoring

- **Time Proximity**: Exponential decay (closer = higher score)
- **Service Matching**: Exact or partial name match
- **Error Code Matching**: Presence in logs/commits
- **File Relevance**: Service name in changed files

### ML-Based (Optional)

- **Anomaly Detection**: Isolation Forest on log patterns
- **Features**: Hour, severity, message length
- **Output**: Unusual log entries flagged

### LLM-Enhanced

- GPT-4.1 Nano provides reasoning for top correlations
- Adds context and patterns humans might miss

## 🎨 Teams Integration

The service generates **Adaptive Cards** for Microsoft Teams:

```json
{
  "type": "AdaptiveCard",
  "body": [
    {
      "type": "TextBlock",
      "text": "🔍 RCA Investigation Results",
      "weight": "bolder"
    },
    ...
  ]
}
```

**Webhook Endpoint**: `/api/v1/teams-webhook`

## 🔐 Security Considerations

1. **API Keys**: Store in `.env`, never commit
2. **Authentication**: Add JWT/OAuth for production
3. **Rate Limiting**: Implement for public APIs
4. **CORS**: Configure `allow_origins` properly
5. **Secrets**: Use Azure Key Vault for production

## 🚨 Error Handling

All agents include comprehensive error handling:

- **Fallback Responses**: System continues even if agents fail
- **Error Aggregation**: All errors tracked in execution context
- **Logging**: Structured logging throughout
- **Partial Results**: Return what's available, flag missing data

## 📝 Logging

Logs use Python's standard logging with levels:

- **DEBUG**: Detailed agent operations
- **INFO**: Major workflow steps
- **WARNING**: Non-critical issues
- **ERROR**: Failures requiring attention

Configure via `LOG_LEVEL` environment variable.

## 🔄 Extending the System

### Add New Agent

1. Create agent file in `agents/`
2. Implement agent class with `execute()` method
3. Add to orchestrator workflow
4. Update models if needed

### Add New Data Source

1. Create integration in `integrations/`
2. Create corresponding LangChain tool in `tools.py`
3. Update correlation engine to use new data

### Customize Correlation

Edit `agents/correlation_engine.py`:
- Adjust scoring weights
- Add new correlation rules
- Enhance ML features

## 📚 Additional Resources

- [LangChain Documentation](https://python.langchain.com/)
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Teams Adaptive Cards](https://adaptivecards.io/)

## 🤝 Contributing

1. Follow existing code structure
2. Add comprehensive comments
3. Include type hints
4. Update models for new data structures
5. Test individual agents before integration

## 📄 License

This is a proprietary system for internal use.

## 🆘 Troubleshooting

### Issue: "Import could not be resolved"

**Solution**: Install dependencies and activate virtual environment

### Issue: "Azure authentication failed"

**Solution**: Check credentials in `.env`, ensure Azure CLI is authenticated

### Issue: "GitHub rate limit exceeded"

**Solution**: Use authenticated token, increase rate limit with GitHub App

### Issue: "No correlations found"

**Solution**: Check time window, verify data is available in sources

## 📧 Support

For questions or issues:
- Check logs in console output
- Review API docs at `/docs`
- Examine individual agent outputs
- Enable DEBUG logging for details
